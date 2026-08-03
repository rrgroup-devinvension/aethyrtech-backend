import logging
import re
from collections import defaultdict

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import (
    RegionDataSchema, CategoryDataRow, AvailabilityRow, 
    PlatformHealthDataset, PlatformHealthScores, 
    TopKeywordRow, TopBrandRow, CategoryViewPayload
)
from experience_cloud.json_generator.utils import ItemGenerator, match_brand

logger = logging.getLogger(__name__)

class BrandMetrics:
    """Aggregates all metrics for a single brand in one pass."""
    def __init__(self, brand: str):
        self.brand = brand
        self.total_price = 0.0
        self.price_count = 0
        self.total_discount = 0.0
        self.discount_count = 0
        self.total_rating = 0.0
        self.rating_count = 0
        self.total_reviews = 0
        self.total_videos = 0
        
        self.sku_count = 0
        self.live_count = 0
        
        self.health_sum = 0
        self.health_count = 0
        
        # Maps platform -> {"total": score, "count": int}
        self.platform_health = defaultdict(lambda: {"total": 0, "count": 0})

def prepare_topkeywords(keywords: list, inverted_index: dict) -> list[TopKeywordRow]:
    """Compute top 5 keywords from `keywords` (ordered list) using an inverted index.

    Ranking metric: total occurrences across product `title`, `description`, and `bullets`.
    Ties are broken by the original order in the `keywords` list (first occurrence wins).
    Returns a list of strictly-typed TopKeywordRow dicts.
    """
    if not keywords:
        return []

    counts = []
    for idx, kw in enumerate(keywords):
        if not kw:
            continue
            
        kw_words = set(re.findall(r'\w+', kw.lower()))
        if not kw_words:
            continue

        # O(1) hash set union lookup!
        matched_products = set()
        for w in kw_words:
            matched_products.update(inverted_index.get(w, set()))
            
        total = len(matched_products)
        counts.append((kw, total, idx))

    # sort by total desc, tie-break by original index asc
    counts.sort(key=lambda x: (-x[1], x[2]))

    top = []
    for kw, total, _ in counts[:5]:
        top.append(TopKeywordRow(keyword=kw, value=total, change=""))
    return top


@handle_builder_exceptions
def category_view_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, CategoryViewPayload]:
    """Construct the JSON payload for the Category View dashboard.

    Aggregates top-level catalog health, keyword frequency, platform-specific availability,
    and competitor brand metrics into a unified summary payload using a blazing fast O(P) single-pass architecture.
    """
    brands = region_data.get("display_brands", [])
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting CATEGORY_VIEW JSON build for task {t_id}")

    platform_schemas = region_data.get("platforms", {})
    platform_codes = list(platform_schemas.keys())
    platform_names = [p.get("platform_name") for p in platform_schemas.values()]

    # O(1) lookup dictionary for brand matching
    valid_brands = {b.lower(): b for b in brands}
    brand_metrics: dict[str, BrandMetrics] = {b: BrandMetrics(b) for b in brands}
    inverted_index = defaultdict(set)

    # SINGLE PASS AGGREGATION
    for p_idx, p in enumerate(products or []):
        # 1. Track Inverted Index for Keywords
        try:
            t = getattr(p, 'title', '') or ''
            d = getattr(p, 'description', '') or ''
            b = " ".join(getattr(p, 'bullets', []) or [])
            combined = f"{t} {d} {b}".lower()
            if combined.strip():
                for word in set(re.findall(r'\w+', combined)):
                    inverted_index[word].add(p_idx)
        except (AttributeError, TypeError, ValueError):
            pass

        # 2. Track Brand Metrics
        if not p.brand:
            continue
            
        b_key = str(p.brand).lower().strip()
        matched_brand = valid_brands.get(b_key)
        
        if not matched_brand:
            continue
            
        m = brand_metrics[matched_brand]
        
        # Build Brand Stats
        if p.selling_price:
            m.total_price += p.selling_price
            m.price_count += 1
        if p.discount_percentage:
            m.total_discount += p.discount_percentage
            m.discount_count += 1
        if p.rating_value:
            m.total_rating += p.rating_value
            m.rating_count += 1
        m.total_reviews += p.review_count or 0
        m.total_videos += p.video_count or 0
        
        # Build Availability & Category Data
        m.sku_count += 1
        is_live = (p.availability_status or "").lower() == "available"
        if is_live:
            m.live_count += 1
            
        # Build Health Scores
        score = p.health_score()
        m.health_sum += score
        m.health_count += 1
        
        platform = (p.platform or "").lower()
        if platform in platform_codes:
            m.platform_health[platform]["total"] += score
            m.platform_health[platform]["count"] += 1

    # RECONSTRUCT PAYLOAD FROM AGGREGATED METRICS
    datasets: list[PlatformHealthDataset] = []
    top_brands: list[TopBrandRow] = []
    availability_data: list[AvailabilityRow] = []
    category_data: list[CategoryDataRow] = []

    total_category_skus = 0
    total_category_live = 0
    total_category_health_sum = 0
    total_category_health_count = 0

    for brand in brands:
        m = brand_metrics[brand]
        
        # 1. Platform Health Scores
        scores = []
        for plat in platform_codes:
            plat_data = m.platform_health[plat]
            if plat_data["count"] == 0:
                scores.append(0)
            else:
                scores.append(round(plat_data["total"] / plat_data["count"]))
        datasets.append(PlatformHealthDataset(label=brand, data=scores))
        
        # 2. Top Brands Stats
        if m.sku_count > 0:
            avg_price = round(m.total_price / m.price_count, 2) if m.price_count else 0
            avg_discount = round(m.total_discount / m.discount_count, 2) if m.discount_count else 0
            avg_rating = round(m.total_rating / m.rating_count, 2) if m.rating_count else 0
            
            top_brands.append(TopBrandRow(
                brand=brand,
                avg_discount=f"{avg_discount}%",
                avg_price=f"₹{avg_price}",
                rating=avg_rating,
                reviews=m.total_reviews,
                videos=m.total_videos
            ))
            
        # 3. Availability
        if m.sku_count > 0:
            availability_data.append(AvailabilityRow({
                "Brand": brand,
                "SKU": str(m.live_count),
                "Not Available": str(m.sku_count - m.live_count)
            }))
            
        # 4. Category Data Row
        if m.sku_count > 0:
            live_percent = round((m.live_count / m.sku_count) * 100) if m.sku_count else 0
            avg_health = round(m.health_sum / m.health_count) if m.health_count else 0
            category_data.append(CategoryDataRow({
                "Audit Name": brand,
                "Frequency": "One Time",
                "SKUs": m.sku_count,
                "Last Run": "31/01/2026",
                "% Live": f"{live_percent}%",
                "Avg Health": avg_health
            }))
            
            total_category_skus += m.sku_count
            total_category_live += m.live_count
            total_category_health_sum += m.health_sum
            total_category_health_count += m.health_count

    # Category Summary Row
    category_live_percent = round((total_category_live / total_category_skus) * 100) if total_category_skus else 0
    category_avg_health = round(total_category_health_sum / total_category_health_count) if total_category_health_count else 0
    category_data.append(CategoryDataRow({
        "Audit Name": "Category",
        "Frequency": "One Time",
        "SKUs": total_category_skus,
        "Last Run": "31/01/2026",
        "% Live": f"{category_live_percent}%",
        "Avg Health": category_avg_health
    }))

    display_keywords = region_data.get("display_keywords", [])
    top_keywords = prepare_topkeywords(display_keywords, inverted_index)
    
    payload: CategoryViewPayload = CategoryViewPayload({
        "Category Data": category_data,
        "Availability": availability_data,
        "PlatformHealthScores": PlatformHealthScores(
            labels=platform_names,
            datasets=datasets
        ),
        "Top Keywords": top_keywords,
        "Top Brands": top_brands,
    })
    
    logger.info(f"Completed CATEGORY_VIEW JSON build for task {t_id}")
    return False, payload
