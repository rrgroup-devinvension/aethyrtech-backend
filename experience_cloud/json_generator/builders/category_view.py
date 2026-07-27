from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator
from typing import List, Dict, Optional, Any, Union
from experience_cloud.json_generator.decorators import handle_builder_exceptions
import logging

from experience_cloud.json_generator.utils import match_brand
import re

logger = logging.getLogger(__name__)


def build_brand_stats(matched_products: list, brand: str) -> Optional[dict]:

    total_price = 0
    price_count = 0
    total_discount = 0
    discount_count = 0
    total_rating = 0
    rating_count = 0
    total_reviews = 0
    total_videos = 0
    
    if not matched_products:
        return None
        
    for p in matched_products:
        if p.selling_price:
            total_price += p.selling_price
            price_count += 1
        if p.discount_percentage:
            total_discount += p.discount_percentage
            discount_count += 1
        if p.rating_value:
            total_rating += p.rating_value
            rating_count += 1
        total_reviews += p.review_count or 0
        total_videos += p.video_count or 0

    avg_price = round(total_price / price_count, 2) if price_count else 0
    avg_discount = round(total_discount / discount_count, 2) if discount_count else 0
    avg_rating = round(total_rating / rating_count, 2) if rating_count else 0
    return {
        "brand": brand,
        "avg_discount": f"{avg_discount}%",
        "avg_price": f"₹{avg_price}",
        "rating": avg_rating,
        "reviews": total_reviews,
        "videos": total_videos
    }

def platform_health_by_brand(matched_products: list, brand: str, platforms: list) -> list:
    stats = {
        p: {"total": 0, "count": 0}
        for p in platforms
    }
    for p in matched_products:
        platform = (p.platform or "").lower()
        if platform not in stats:
            continue
        score = p.health_score()
        stats[platform]["total"] += score
        stats[platform]["count"] += 1
    scores = []
    for platform in platforms:
        entry = stats[platform]
        if entry["count"] == 0:
            scores.append(0)
        else:
            avg = round(entry["total"] / entry["count"])
            scores.append(avg)
    return scores



def build_availability_by_brand(brand_products_map: dict, brands: list) -> list:
    result = []
    for brand in brands:
        matched_products = brand_products_map.get(brand, [])
        if not matched_products:
            continue
            
        available_count = 0
        unavailable_count = 0
        for p in matched_products:
            status = (p.availability_status or "").lower()
            if status == "available":
                available_count += 1
            else:
                unavailable_count += 1
                
        result.append({
            "Brand": brand,
            "SKU": str(available_count),
            "Not Available": str(unavailable_count)
        })
    return result


def build_category_data(brand_products_map: dict, brands: list) -> list:
    result = []
    total_skus = 0
    total_live = 0
    total_health = 0
    total_health_count = 0
    
    for brand in brands:
        matched_products = brand_products_map.get(brand, [])
        if not matched_products:
            continue
            
        sku_count = 0
        live_count = 0
        health_sum = 0
        health_count = 0
        
        for p in matched_products:
            sku_count += 1
            # Availability
            if (p.availability_status or "").lower() == "available":
                live_count += 1
            # Health Score
            score = p.health_score()
            health_sum += score
            health_count += 1
            
        live_percent = round((live_count / sku_count) * 100) if sku_count else 0
        avg_health = round(health_sum / health_count) if health_count else 0
        result.append({
            "Audit Name": brand,
            "Frequency": "One Time",
            "SKUs": sku_count,
            "Last Run": "31/01/2026",
            "% Live": f"{live_percent}%",
            "Avg Health": avg_health
        })
        # ---------- CATEGORY TOTAL ----------
        total_skus += sku_count
        total_live += live_count
        total_health += health_sum
        total_health_count += health_count
        
    # ---------- CATEGORY SUMMARY ROW ----------
    category_live_percent = round((total_live / total_skus) * 100) if total_skus else 0
    category_avg_health = round(total_health / total_health_count) if total_health_count else 0
    result.append({
        "Audit Name": "Category",
        "Frequency": "One Time",
        "SKUs": total_skus,
        "Last Run": "31/01/2026",
        "% Live": f"{category_live_percent}%",
        "Avg Health": category_avg_health
    })

    return result




def prepare_topkeywords(keywords: list, products: ItemGenerator) -> list:
    """Compute top 5 keywords from `keywords` (ordered list).

    Ranking metric: total occurrences across product `title`, `description`, and `bullets`.
    Ties are broken by the original order in the `keywords` list (first occurrence wins).
    Returns a list of dicts: {"keyword": str, "value": int, "change": str}.
    """
    if not keywords:
        return []
        
    # Pre-parse all products into sets of words (O(P) regex operations instead of O(P * K))
    product_word_sets = []
    for p in products or []:
        try:
            t = getattr(p, 'title', '') or ''
            d = getattr(p, 'description', '') or ''
            b = " ".join(getattr(p, 'bullets', []) or [])
            combined = f"{t} {d} {b}".lower()
            product_words = set(re.findall(r'\w+', combined))
            if product_words:
                product_word_sets.append(product_words)
        except Exception:
            continue
            
    # Pre-parse keywords
    kw_word_lists = []
    for kw in keywords:
        if kw:
            kw_words = re.findall(r'\w+', kw.lower())
            if kw_words:
                kw_word_lists.append((kw, kw_words))
            
    counts = []
    for idx, (kw, kw_words) in enumerate(kw_word_lists):
        # O(1) hash set lookup
        total = sum(
            1 for product_words in product_word_sets
            if any(w in product_words for w in kw_words)
        )
        counts.append((kw, total, idx))

    # sort by total desc, tie-break by original index asc
    counts.sort(key=lambda x: (-x[1], x[2]))

    top = []
    for kw, total, _ in counts[:5]:
        top.append({"keyword": kw, "value": int(total), "change": ""})
    return top



@handle_builder_exceptions
def category_view_builder(region_data: RegionDataSchema, task, products=None, template="template-name") -> tuple[bool, dict]:
    brands = region_data.get("display_brands", [])
    keywords = region_data.get("keywords", [])
    brand_id = region_data.get("brand_id")
    brand_name = region_data.get("brand_name")
    
    """Build category view JSON and save."""
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting CATEGORY_VIEW JSON build for task {t_id}")
    
    # Extract platforms directly from region_data schema
    platform_schemas = region_data.get("platforms", {})
        
    platform_codes = list(platform_schemas.keys())
    platform_names = [p.get("platform_name") for p in platform_schemas.values()]
    
    top_brands = []
    datasets = []
    
    # O(P*B) Grouping exactly once rather than looping in every aggregator
    brand_products_map = {b: [] for b in brands}
    for p in products:
        if not p.brand: continue
        for b in brands:
            if match_brand(b, p.brand):
                brand_products_map[b].append(p)
                break
    
    for brand in brands:
        matched_products = brand_products_map.get(brand, [])
        health_scores = platform_health_by_brand(matched_products, brand, platform_codes)
        datasets.append({ "label": brand, "data": health_scores})

    for b in brands:
        matched_products = brand_products_map.get(b, [])
        stats = build_brand_stats(matched_products, b)
        if stats:
            top_brands.append(stats)

    display_keywords = region_data.get("display_keywords", [])
    top_keywords = prepare_topkeywords(display_keywords, products)
    payload = {
        "Category Data": build_category_data(brand_products_map, brands),
        "Availability": build_availability_by_brand(brand_products_map, brands),
        "PlatformHealthScores": {
            "labels": platform_names,
            "datasets": datasets
        },
        "Top Keywords": top_keywords,
        "Top Brands": top_brands,   
    }
    logger.info(f"Completed CATEGORY_VIEW JSON build for task {t_id}")
    return False, payload
