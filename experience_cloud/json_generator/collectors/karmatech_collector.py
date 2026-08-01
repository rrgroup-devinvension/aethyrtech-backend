import logging

from experience_cloud.json_generator.schemas import ProductSchema, RegionDataSchema
from experience_cloud.json_generator.utils import match_brands
from experience_cloud.market_integrations.models.karmatech import (
    KarmatechProduct,
    KarmatechProductRanking,
    KarmatechReview,
)

logger = logging.getLogger(__name__)

def get_all_karmatech_products(region_data: RegionDataSchema) -> list[ProductSchema]:
    """Retrieve localized product data and analytics from the Karmatech primary database.

    Extracts recent product metrics, keyword search rankings, and verified customer reviews
    for authorized brand portfolios, aggressively normalizing the output into a unified list
    of standardized ProductSchema instances.
    """
    brands: dict[str, list[str]] = region_data.get("brands", {})
    if not brands:
        return []

    ctx = f"[JSON Gen Collector | Brand: {region_data.get('brand_name', 'Unknown')}]"

    keywords_map = {}
    for plat_code, plat in region_data.get("platforms", {}).items():
        if plat_code:
            keywords_map[plat_code] = [kw["name"] for kw in plat.get("keywords", []) if kw.get("name")]

    # Find the latest scraper_id
    latest_product = KarmatechProduct.objects.filter(brand__in=brands).order_by('-scraper_id').first()
    if not latest_product:
        return []

    scraper_id = latest_product.scraper_id
    scraped_date = latest_product.scraped_date
    if scraped_date:
        from datetime import datetime
        if isinstance(scraped_date, str):
            try:
                scraped_date = datetime.strptime(scraped_date[:10], "%Y-%m-%d").date()
            except ValueError:
                scraped_date = None
        elif isinstance(scraped_date, datetime):
            scraped_date = scraped_date.date()

    products = KarmatechProduct.objects.filter(scraper_id=scraper_id, brand__in=brands)
    if not products.exists():
        return []

    skus = [p.sku for p in products]

    rankings_qs = KarmatechProductRanking.objects.select_related('keyword').filter(sku__in=skus, scraper_id=scraper_id)
    reviews_qs = KarmatechReview.objects.filter(sku__in=skus)

    ranking_map: dict[str, list[dict]] = {}
    for r in rankings_qs:
        ranking_entry = {
            "platform": r.platform,
            "keyword": getattr(r.keyword, "keyword", None),
            "rank": r.position,
            "page": r.page
        }
        ranking_map.setdefault(r.sku, []).append(ranking_entry)

    review_map: dict[str, list[dict]] = {}
    for rev in reviews_qs:
        review_entry = {
            "id": rev.id,
            "product_id": rev.product_id,
            "sku": rev.sku,
            "platform": rev.platform,
            "review_id": rev.review_id,
            "reviewer_name": rev.reviewer_name,
            "rating": float(rev.rating) if rev.rating else 0,
            "review_title": rev.review_title,
            "review_text": rev.review_text,
            "review_date": rev.review_date,
            "verified_purchase": rev.verified_purchase,
            "helpful_count": rev.helpful_count,
            "review_images": rev.review_images if rev.review_images else []
        }
        review_map.setdefault(rev.sku, []).append(review_entry)

    formatted_products = []
    for p in products:
        sku = p.sku
        matched_brand = match_brands(brands, p.brand)
        if not matched_brand:
            logger.error(f"{ctx} Product {p.sku} skipped due to brand mismatch ({p.brand})")
            continue

        pf = ProductSchema()
        pf.set_basic(
            uid=sku,
            keywords=keywords_map.get(p.platform) or [],
            status=p.is_active,
            target_keyword=None,
            platform=p.platform,
            brand=matched_brand or p.brand,
            title=p.title,
            description=p.description,
            product_url=p.product_url,
            platform_type="marketplace",
            scraped_date=scraped_date,
            scraper_id=scraper_id,
            platform_assured=str(p.amazon_choice)
        )
        pf.set_price(p.price, p.sale_price)
        pf.set_media(
            images=p.image_urls,
            thumbnail=None,
            main_image=None,
            image_count=len(p.image_urls) if isinstance(p.image_urls, list) else 0,
            video_count=len(p.video_urls) if isinstance(p.video_urls, list) else 0
        )
        pf.set_rating_direct(p.rating, p.review_count)
        pf.set_bullets(p.highlights if isinstance(p.highlights, list) else [])
        pf.set_category(category=p.category)
        pf.set_detail(
            model=p.model_name,
            manufacturer_part=p.manufacturer,
            sold_by=p.seller_name,
            shipped_by=None
        )
        product_rankings = ranking_map.get(sku, [])
        pf.set_rankings({
            "000000": product_rankings
        })
        if sku in review_map:
            pf.set_reviews(review_map[sku])

        is_avaible_correct = pf.set_availability(p.inventory_status)
        if is_avaible_correct:
            formatted_products.append(pf)
        else:
            logger.error(f"{ctx} Product {p.sku} availability mismatch")

    return formatted_products
