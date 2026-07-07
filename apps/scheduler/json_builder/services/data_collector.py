import logging
import json
import pickle
import tempfile
import os
from apps.scheduler.json_builder.utils import mysql_connection
from apps.scheduler.utility.tasks_utility import match_brands
from apps.scheduler.json_builder.services.product_formatter import ProductFormatter
from apps.scheduler.models import QuickCommerceProduct
from apps.category.models import CategoryKeyword
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

logger = logging.getLogger(__name__)

def chunked_queryset(queryset, chunk_size=2000):
    last_pk = 0
    while True:
        chunk = list(queryset.filter(pk__gt=last_pk).order_by('pk')[:chunk_size])
        if not chunk:
            break
        for obj in chunk:
            yield obj
        last_pk = chunk[-1].pk

class DiskBackedIterable:
    def __init__(self, generator_func, *args, **kwargs):
        fd, self.filepath = tempfile.mkstemp(suffix=".pkl")
        os.close(fd)
        with open(self.filepath, 'wb') as f:
            for item in generator_func(*args, **kwargs):
                pickle.dump(item, f)
                
    def __iter__(self):
        with open(self.filepath, 'rb') as f:
            while True:
                try:
                    yield pickle.load(f)
                except EOFError:
                    break
                    
    def __del__(self):
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
        except Exception:
            pass

def get_all_quick_products(keywords, pincodes, brands):
    qs = QuickCommerceProduct.objects.select_related("detail").filter(
        platform="noon_ksa"
    )

    qs = qs.order_by("product_uid")
    
    scraper_id = None
    scraped_date = None
    
    current_uid = None
    current_pf = None

    for p in chunked_queryset(qs, chunk_size=1000):
        d = getattr(p, "detail", None)
        if scraped_date is None:
            scraped_date = p.created_at
            scraper_id = p.search.id
        matched_brand = match_brands(brands, p.brand)
        if not matched_brand:
            log_error(task_id=None, error='Product skipped due to brand mismatch', extra={
                'product_uid': p.product_uid,
                'brand': p.brand
            })
            continue
        if p.keyword not in keywords.get(p.platform, []) or p.pincode not in pincodes.get(p.platform, []):
            log_error(task_id=None, error='Product skipped due to keyword/pincode mismatch', extra={
                'product_uid': p.product_uid,
                'keyword': p.keyword,
                'pincode': p.pincode,
                'brand': p.brand
            })
            continue
            
        product_uid = p.product_uid
        ranking_entry = {
            "platform": p.platform,
            "keyword": p.keyword,
            "rank": p.rank if p.rank <=32 else 0,
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
        current_pf = ProductFormatter()
        current_pf.set_basic(
            uid=p.product_uid,
            keywords=keywords.get(p.platform) or [],
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
        is_available_correct = current_pf.set_availability(p.availability)
        current_pf._is_available_correct = is_available_correct
        
    if current_pf is not None and getattr(current_pf, "_is_available_correct", False):
        yield current_pf

def get_all_market_products(keywords, pincodes, brands):
    scraper_id = None
    scraped_date = None
    with mysql_connection() as conn:
        cursor = conn.cursor()
        placeholders = ",".join(["%s"] * len(brands))
        cursor.execute(f"""
            SELECT scraper_id, scraped_date
            FROM products
            WHERE brand IN ({placeholders})
            ORDER BY scraper_id DESC
            LIMIT 1
        """, brands)
        latest = cursor.fetchone()
        if not latest:
            return []
        scraper_id = latest["scraper_id"]
        scraped_date = latest["scraped_date"]
        cursor.execute("""
            SELECT *
            FROM products
            WHERE scraper_id = %s
        """, (scraper_id,))
        products = cursor.fetchall()
        if not products:
            return []
        skus = [p["sku"] for p in products]
        fmt = ",".join(["%s"] * len(skus))
        cursor.execute(f"""
            SELECT 
                pr.product_id,
                pr.sku,
                pr.platform,
                pr.position,
                pr.page,
                k.keyword
            FROM product_rankings pr
            JOIN keywords k ON pr.keyword_id = k.id
            WHERE pr.sku IN ({fmt})
              AND pr.scraper_id = %s
        """, (*skus, scraper_id))
        rankings = cursor.fetchall()
        cursor.execute(f"""
            SELECT 
                id,
                product_id,
                sku,
                platform,
                review_id,
                reviewer_name,
                rating,
                review_title,
                review_text,
                review_date,
                verified_purchase,
                helpful_count,
                review_images
            FROM reviews
            WHERE sku IN ({fmt})
        """, skus)
        reviews = cursor.fetchall()
    ranking_map = {}
    for r in rankings:
        ranking_entry = {
            "platform": r["platform"],
            "keyword": r["keyword"],
            "rank": r["position"],
            "page": r["page"]
        }
        ranking_map.setdefault(r["sku"], []).append(ranking_entry)
    review_map = {}
    for r in reviews:
        review_entry = {
            "id": r["id"],
            "product_id": r["product_id"],
            "sku": r["sku"],
            "platform": r["platform"],
            "review_id": r["review_id"],
            "reviewer_name": r["reviewer_name"],
            "rating": float(r["rating"]) if r["rating"] else 0,
            "review_title": r["review_title"],
            "review_text": r["review_text"],
            "review_date": r["review_date"],
            "verified_purchase": r["verified_purchase"],
            "helpful_count": r["helpful_count"],
            "review_images": json.loads(r["review_images"]) if r["review_images"] else []
        }
        review_map.setdefault(r["sku"], []).append(review_entry)
    formatted_products = []
    for p in products:
        sku = p["sku"]
        matched_brand = match_brands(brands, p["brand"])
        if not matched_brand:
            log_error(task_id=None, error='Product skipped due to brand mismatch', extra={
                'product_uid': p["id"],
                'brand': p["brand"]
            })
            continue 
        pf = ProductFormatter()
        pf.set_basic(
            uid=sku,
            keywords=keywords.get(p["platform"]) or [],
            status=p['is_active'],
            target_keyword=None,
            platform=p["platform"],
            brand=matched_brand or p["brand"],
            title=p["title"],
            description=p.get("description"),
            product_url=p["product_url"],
            platform_type="marketplace",
            scraped_date=scraped_date,
            scraper_id=scraper_id,
            platform_assured=p['amazon_choice']
        )
        pf.set_price(p["price"], p["sale_price"])
        pf.set_rating_direct(p["rating"], p["review_count"])
        pf.set_media(images=p["image_urls"], videos=p["video_urls"])
        pf.set_bullets(p['highlights'])
        pf.set_category(category=p["category"])
        pf.set_detail(
            model=p['model_name'],
            manufacturer_part=p['manufacturer'],
            sold_by=p['seller_name'],
            shipped_by=None
        )
        product_rankings = ranking_map.get(sku, [])
        pf.set_rankings({
            "000000": product_rankings
        })
        if sku in review_map:
            pf.set_reviews(review_map[sku])
        is_avaible_correct = pf.set_availability(p["inventory_status"])
        if is_avaible_correct:
            formatted_products.append(pf)
        else:
            log_error(task_id=None, error='Availability mismatch', extra={
                'product_uid': p["id"],
                'value': p["inventory_status"]
            })
    return formatted_products

def get_all_products_generator(platform_type, keywords, pincodes, brands):
    index = 1
    if "quick_commerce" in platform_type:
        for pf in get_all_quick_products(keywords, pincodes, brands):
            pf.id = index
            index += 1
            yield pf
    if "marketplace" in platform_type:
        for pf in get_all_market_products(keywords, pincodes, brands):
            pf.id = index
            index += 1
            yield pf

def get_all_products(platform_type, keywords, pincodes, brands):
    platform_type = platform_type or []
    if isinstance(platform_type, str):
        platform_type = [platform_type]
    
    return DiskBackedIterable(get_all_products_generator, platform_type, keywords, pincodes, brands)
