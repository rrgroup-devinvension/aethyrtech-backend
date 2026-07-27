import logging
from typing import Generator, Any
from django.db.models.query import QuerySet
from experience_cloud.json_generator.schemas import RegionDataSchema, ProductSchema
from experience_cloud.json_generator.utils import match_brands
from experience_cloud.market_integrations.models.xbytes import XBytesProduct

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
        
    ctx = f"[JSON Gen Collector | Brand: {region_data.get('brand_name', 'Unknown')}]"
        
    keywords_map = {}
    pincodes_map = {}
    for plat_code, plat in region_data.get("platforms", {}).items():
        if plat_code:
            keywords_map[plat_code] = [kw.get("name") for kw in plat.get("keywords", [])]
            pincodes_map[plat_code] = [loc.get("name") for loc in plat.get("locations", [])]

    platforms = list(keywords_map.keys())
    qs = XBytesProduct.objects.filter(platform__in=platforms).order_by("product_uid")
    
    scraper_id = None
    scraped_date = None
    
    current_uid = None
    current_pf = None

    for p in chunked_queryset(qs, chunk_size=1000):
        if scraped_date is None:
            scraped_date = p.created_at
            scraper_id = None  # Removed search relation
            
        matched_brand = match_brands(brands, p.brand)
        if not matched_brand:
            logger.error(f"{ctx} Product {p.product_uid} skipped due to brand mismatch ({p.brand})")
            continue
            
        product_uid = p.product_uid
        ranking_entry = {
            "platform": p.platform,
            "keyword": p.keyword,
            "rank": p.rank if p.rank and p.rank <= 32 else 0,
            "page": 1
        }
        ranking_data = {
            p.location or "000000": [ranking_entry]
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
            description=p.description,
            product_url=p.product_url,
            platform_type="quick_commerce",
            scraped_date=scraped_date,
            scraper_id=scraper_id,
            platform_assured=None
        )
        current_pf.set_price(p.mrp, p.sell_price)
        current_pf.set_media(
            images=p.images,
            thumbnail=p.thumbnail,
            main_image=p.main_image,
            image_count=p.image_count,
            video_count=p.video_count
        )
        val_rating = p.rating if p.rating and str(p.rating).strip() not in ("0", "0.0", "NA") else p.brand_rating
        val_reviews = p.reviews if p.reviews and str(p.reviews).strip() not in ("0", "0.0", "NA") else p.brand_reviews
        
        current_pf.set_rating_direct(val_rating, val_reviews)
        current_pf.set_bullets(p.bullets if p.bullets else [])
        current_pf.set_category(category=p.category)
        current_pf.set_detail(
            model=p.model,
            manufacturer_part=p.manufacturer_part,
            sold_by=p.sold_by,
            shipped_by=p.shipped_by
        )
        current_pf.set_rankings(ranking_data)
        is_avaible_correct = current_pf.set_availability(p.availability)
        current_pf._is_available_correct = is_avaible_correct
        if not is_avaible_correct:
             logger.error(f"{ctx} Product {p.product_uid} availability mismatch")
            
    if current_pf is not None and getattr(current_pf, "_is_available_correct", False):
        yield current_pf
