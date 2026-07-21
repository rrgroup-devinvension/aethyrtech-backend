import logging
from typing import Generator, Any
from django.db.models.query import QuerySet
from experience_cloud.json_generator.schemas import RegionDataSchema, ProductSchema
from experience_cloud.json_generator.utils import match_brands
from experience_cloud.market_integrations.models.xbytes import XBytesProduct
from experience_cloud.json_generator.log_manager import log_error

logger = logging.getLogger(__name__)

def chunked_queryset(queryset: QuerySet, chunk_size: int = 1000) -> Generator[Any, None, None]:
    pk = 0
    while True:
        chunk = list(queryset.filter(pk__gt=pk).order_by('pk')[:chunk_size])
        if not chunk:
            break
        for obj in chunk:
            yield obj
        pk = chunk[-1].pk

def get_all_xbytes_products(region_data: RegionDataSchema) -> Generator[ProductSchema, None, None]:
    brands = region_data.get('brands', [])
    if not brands:
        return
        
    keywords_map = {}
    pincodes_map = {}
    for plat in region_data.get("platforms", []):
        plat_name = plat.get("platform_name")
        if plat_name:
            keywords_map[plat_name] = [kw.get("name") for kw in plat.get("keywords", [])]
            pincodes_map[plat_name] = [loc.get("name") for loc in plat.get("locations", [])]

    qs = XBytesProduct.objects.select_related("detail", "search").filter(brand__in=brands).order_by("product_uid")
    
    scraper_id = None
    scraped_date = None
    
    current_uid = None
    current_pf = None

    for p in chunked_queryset(qs, chunk_size=1000):
        d = getattr(p, "detail", None)
        if scraped_date is None:
            scraped_date = p.created_at
            scraper_id = p.search.id if getattr(p, "search", None) else None
            
        matched_brand = match_brands(brands, p.brand)
        if not matched_brand:
            log_error(task_id=None, error='Product skipped due to brand mismatch', extra={
                'product_uid': p.product_uid,
                'brand': p.brand
            })
            continue
            
        product_uid = p.product_uid
        ranking_entry = {
            "platform": p.platform,
            "keyword": p.keyword,
            "rank": p.rank if p.rank <= 32 else 0,
            "page": 1
        }
        ranking_data = {
            p.pincode or "000000": [ranking_entry]
        }
        
        if current_uid == product_uid:
            existing_rankings = current_pf.rankings or {}
            for pin, ranks in ranking_data.items():
                if pin not in existing_rankings:
                    existing_rankings[pin] = ranks
                else:
                    existing_keys = { (r["platform"], r["keyword"]) for r in existing_rankings[pin] }
                    for r in ranks:
                        key = (r["platform"], r["keyword"])
                        if key not in existing_keys:
                            existing_rankings[pin].append(r)
            current_pf.set_rankings(existing_rankings)
            continue
            
        if current_pf is not None and getattr(current_pf, "_is_available_correct", False):
            yield current_pf
            
        current_uid = product_uid
        current_pf = ProductSchema()
        current_pf.set_basic(
            uid=p.product_uid,
            keywords=keywords_map.get(p.platform) or [],
            status=1,
            target_keyword=p.keyword,
            platform=p.platform,
            brand=matched_brand or p.brand,
            title=p.title,
            description=d.description if d else None,
            product_url=p.product_url,
            platform_type="quick_commerce",
            scraped_date=scraped_date,
            scraper_id=scraper_id,
            platform_assured=None
        )
        current_pf.set_price(p.msrp, p.sell_price)
        current_pf.set_media(
            images=p.detail_page_images,
            thumbnail=p.thumbnail,
            main_image=p.main_image,
            image_count=d.image_count if d else 0,
            video_count=d.video_count if d else 0
        )
        val_rating = p.rating if p.rating and str(p.rating).strip() not in ("0", "0.0", "NA") else p.brand_rating
        val_reviews = p.reviews if p.reviews and str(p.reviews).strip() not in ("0", "0.0", "NA") else p.brand_reviews
        
        current_pf.set_rating_direct(val_rating, val_reviews)
        current_pf.set_bullets(d.bullets if d else [])
        current_pf.set_category(category=p.category)
        current_pf.set_detail(
            model=d.model if d else None,
            manufacturer_part=getattr(d, "manufacturer_part", None),
            sold_by=d.sold_by if d else None,
            shipped_by=d.shipped_by if d else None
        )
        current_pf.set_rankings(ranking_data)
        is_avaible_correct = current_pf.set_availability(p.availability)
        current_pf._is_available_correct = is_avaible_correct
        if not is_avaible_correct:
             log_error(task_id=None, error='Availability mismatch', extra={
                'product_uid': p.product_uid,
                'value': p.availability
            })
            
    if current_pf is not None and getattr(current_pf, "_is_available_correct", False):
        yield current_pf
