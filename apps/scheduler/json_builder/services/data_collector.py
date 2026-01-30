import logging
from apps.scheduler.json_builder.utils import mysql_connection
from apps.scheduler.json_builder.services.product_formatter import ProductFormatter
from apps.scheduler.models import QuickCommerceProduct
from apps.category.models import CategoryKeyword

logger = logging.getLogger(__name__)

def get_all_quick_products(keywords, brands):
    qs = QuickCommerceProduct.objects.select_related("detail")
    products = []
    scraper_id = None
    scraped_date = None
    for p in qs.iterator(chunk_size=500):
        d = getattr(p, "detail", None)
        if scraped_date==None:
            scraped_date = p.created_at
        pf = ProductFormatter()
        pf.set_basic(
            uid=p.product_uid,
            keywords=keywords.get(p.platform) or [],
            status=1,
            target_keyword=p.keyword,
            platform=p.platform,
            brand=p.brand,
            title=p.title,
            description=d.description,
            availability=p.availability,
            product_url=p.product_url,
            platform_type="quick_commerce",
            scraped_date=scraped_date, 
            scraper_id=scraper_id,
            platform_assured=None
        )
        pf.set_price(p.msrp, p.sell_price)
        pf.set_media(images=p.detail_page_images,thumbnail=p.thumbnail, main_image=p.main_image, image_count=d.image_count,video_count=d.video_count)
        pf.set_rating_direct(p.rating, p.reviews)
        pf.set_bullets(d.bullets)
        pf.set_category(category=p.category)
        pf.set_detail(model=d.model, manufacturer_part=d.manufacturer_part, sold_by=d.sold_by, shipped_by=d.shipped_by)
        products.append(pf)
    return products

def get_all_market_products(keywords, brands):
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
        product_ids = [p["id"] for p in products]
        fmt = ",".join(["%s"] * len(product_ids))
        cursor.execute(f"""
            SELECT 
                pr.product_id,
                pr.platform,
                pr.position,
                pr.page,
                k.keyword
            FROM product_rankings pr
            JOIN keywords k ON pr.keyword_id = k.id
            WHERE pr.product_id IN ({fmt})
              AND pr.scraper_id = %s
        """, (*product_ids, scraper_id))
        rankings = cursor.fetchall()
    ranking_map = {}
    for r in rankings:
        product_id = r["product_id"]
        ranking_entry = {
            "platform": r["platform"],
            "keyword": r["keyword"],
            "rank": r["position"],
            "page": r["page"]
        }
        ranking_map.setdefault(product_id, []).append(ranking_entry)
    formatted_products = []
    for p in products:
        product_id = p["id"]
        sku = p["sku"]   # you are using sku as pincode
        pf = ProductFormatter()
        pf.set_basic(
            uid=sku,
            keywords=keywords.get(p["platform"]) or [],
            status=p['is_active'],
            target_keyword=None,
            platform=p["platform"],
            brand=p["brand"],
            title=p["title"],
            description=p.get("description"),
            availability=p["inventory_status"],
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
        product_rankings = ranking_map.get(product_id, [])
        pf.set_rankings({
            "000000": product_rankings
        })
        formatted_products.append(pf)
    return formatted_products

def get_all_products(platform_type, keywords, brands):
    platform_type = platform_type or []
    if isinstance(platform_type, str):
        platform_type = [platform_type]
    products = []
    # if "quick_commerce" in platform_type:
    #     products.extend(get_all_quick_products(keywords, brands))
    if "marketplace" in platform_type:
        products.extend(get_all_market_products(keywords, brands))
    
    for index, pf in enumerate(products, start=1):
        pf.id = index
    return products
