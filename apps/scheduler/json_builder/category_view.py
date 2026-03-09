
import logging
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.utility.tasks_utility import match_brand, get_platform_list
from apps.scheduler.json_builder.keyword_counts import count_occurrence
from django.utils import timezone
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

logger = logging.getLogger(__name__)


def build_brand_stats(products, brand):

    total_price = 0
    price_count = 0
    total_discount = 0
    discount_count = 0
    total_rating = 0
    rating_count = 0
    total_reviews = 0
    total_videos = 0
    found = False
    for p in products:
        if not p.brand or not match_brand(brand, p.brand):
            continue
        found = True
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
    if not found:
        return None
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

def platform_health_by_brand(products, brand, platforms):
    stats = {
        p: {"total": 0, "count": 0}
        for p in platforms
    }
    for p in products:
        if not p.brand or not match_brand(brand, p.brand):
            continue
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

def format_platform_titles(platforms):
    return [p.replace("_", " ").title().replace(" ", "") for p in platforms]

def build_availability_by_brand(products, brands):
    result = []
    for brand in brands:
        available_count = 0
        unavailable_count = 0
        found = False
        for p in products:
            if not p.brand or not match_brand(brand, p.brand):
                continue
            found = True
            status = (p.availability_status or "").lower()
            if status == "available":
                available_count += 1
            else:
                unavailable_count += 1
        if not found:
            continue
        result.append({
            "Brand": brand,
            "SKU": str(available_count),
            "Not Available": str(unavailable_count)
        })
    return result


def build_category_data(products, brands):
    result = []
    total_skus = 0
    total_live = 0
    total_health = 0
    total_health_count = 0
    for brand in brands:
        sku_count = 0
        live_count = 0
        health_sum = 0
        health_count = 0
        last_run = None
        found = False
        for p in products:
            if not p.brand or not match_brand(brand, p.brand):
                continue
            found = True
            sku_count += 1
            # Availability
            if (p.availability_status or "").lower() == "available":
                live_count += 1
            # Health Score
            score = p.health_score()
            health_sum += score
            health_count += 1
            # Last Run Date
            # if p.scraped_date:
            #     if not last_run or p.scraped_date > last_run:
            #         last_run = p.scraped_date
        if not found:
            continue
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

def get_combined_keyword(keywords, platforms):
    combined_keywords = []
    seen = set()
    try:
        # `keywords` is expected to be a mapping: platform -> list of keywords
        if isinstance(keywords, dict):
            for p in platforms:
                platform_kws = keywords.get(p) or []
                for kw in platform_kws:
                    if not kw:
                        continue
                    if kw in seen:
                        continue
                    seen.add(kw)
                    combined_keywords.append(kw)
        else:
            # fallback: if keywords is a flat list, preserve its order
            for kw in (keywords or []):
                if not kw:
                    continue
                if kw in seen:
                    continue
                seen.add(kw)
                combined_keywords.append(kw)
    except Exception:
        logger.exception('Failed to build combined keywords list')
    return combined_keywords


def prepare_topkeywords(keywords, products):
    """Compute top 5 keywords from `keywords` (ordered list).

    Ranking metric: total occurrences across product `title`, `description`, and `bullets`.
    Ties are broken by the original order in the `keywords` list (first occurrence wins).
    Returns a list of dicts: {"keyword": str, "value": int, "change": str}.
    """
    if not keywords:
        return []
    counts = []
    for idx, kw in enumerate(keywords):
        if not kw:
            continue
        total = 0
        for p in products or []:
            try:
                total += count_occurrence(getattr(p, 'title', '') or '', kw)
                total += count_occurrence(getattr(p, 'description', '') or '', kw)
                bullets_text = " ".join(getattr(p, 'bullets', []) or [])
                total += count_occurrence(bullets_text, kw)
            except Exception:
                # ignore errors on individual products
                continue
        counts.append((kw, total, idx))

    # sort by total desc, tie-break by original index asc
    counts.sort(key=lambda x: (-x[1], x[2]))

    top = []
    for kw, total, _ in counts[:5]:
        top.append({"keyword": kw, "value": int(total), "change": ""})
    return top



def category_view_data_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template="catalog", platform_type=None):
    """Build category view JSON and save."""
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting CATEGORY_VIEW JSON build for task {t_id}")
    log_start(task_id=t_id, info={"brand_id": brand_id, "template": template})
    # Build payload using DB aggregates
    try:
        top_brands = []
        platforms = get_platform_list(platform_type)
        platforms = [p for p in platforms]
        datasets = []
        for brand in brands:
            health_scores = platform_health_by_brand(products, brand, platforms)
            datasets.append({ "label": brand, "data": health_scores})

        for b in brands:
            stats = build_brand_stats(products, b)
            if stats:
                top_brands.append(stats)

        combined_keywords = get_combined_keyword(keywords, platforms)

        top_keywords = prepare_topkeywords(combined_keywords, products)
        payload = {
            "Category Data": build_category_data(products, brands),
            "Availability": build_availability_by_brand(products, brands),
            "PlatformHealthScores": {
                "labels": format_platform_titles(platforms),
                "datasets": datasets
            },
            "Top Keywords": top_keywords,
            "Top Brands": top_brands,   
        }
        logger.info(f"Completed CATEGORY_VIEW JSON build for task {t_id}")
        log_success(task_id=t_id, info={"brand_id": brand_id, "template": template})
        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except Exception:
        logger.exception('Failed to build CATEGORY_VIEW JSON')
        log_error(task_id=t_id, error='Failed to build CATEGORY_VIEW JSON')
        raise