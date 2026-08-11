import random
from typing import Any

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.models import TemplateCodes
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import save_or_update_region_json, serve_region_template


@handle_builder_exceptions
def risk_data_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Compile a comprehensive risk and catalog health data payload.

    Aggregates product pincode data, catalog health scores, and keyword SEO blindspots
    to calculate actionable brand anxiety scores and benchmark against competitors.
    """
    # ===============================
    # BRAND (MATCH PHP)
    # ===============================
    current_brand = region_data.get("brand_name")
    region_id = region_data.get("region_id")
    assert current_brand is not None

    if not region_id:
        raise ValueError("Region ID is required.")

    # ===============================
    # 1. LOAD DATA (same as PHP)
    # ===============================
    try:
        pincode_data = serve_region_template(
            region_id, TemplateCodes.CARTESIAN_PRODUCTS_PINCODES.value
        )
    except Exception as e:
        raise ValueError("Failed to load pincode data") from e

    try:
        catalog_data = serve_region_template(
            region_id, TemplateCodes.CATALOG.value
        )
    except Exception as e:
        raise ValueError("Failed to load catalog data") from e

    try:
        keyword_data: dict[str, Any] = serve_region_template(
            region_id, TemplateCodes.KEYWORD_COUNTS.value
        )
    except (OSError, ValueError):
        keyword_data = {}

    # ===============================
    # VALIDATION
    # ===============================
    if "Sheet1" not in pincode_data:
        raise ValueError("cartesian_products_pincodes.json missing 'Sheet1' key.")

    rows = pincode_data["Sheet1"]

    brands = list({r.get("Brand") for r in rows if r.get("Brand")})
    total_listing_count = len(rows)

    all_brand_stats: dict[str, Any] = {}

    # ===============================
    # HELPERS (same as PHP)
    # ===============================
    def get_brand_catalog(brand_name):
        for key, items in catalog_data.items():
            if brand_name.lower() in key.lower():
                return items
        return []

    def get_brand_keywords(brand_name):
        brand_kws = {}

        for store in keyword_data.values():
            for title, kws in store.items():
                if brand_name.lower() in title.lower():
                    for kw_item in kws:
                        kw = kw_item["keyword"]
                        total = (
                            kw_item["counts"]["title"]
                            + kw_item["counts"]["description"]
                            + kw_item["counts"]["bullets"]
                        )

                        if kw not in brand_kws:
                            brand_kws[kw] = {"total": 0, "present": 0}

                        brand_kws[kw]["total"] += 1
                        if total > 0:
                            brand_kws[kw]["present"] += 1

        return brand_kws

    # ===============================
    # MAIN LOOP
    # ===============================
    for b in brands:

        brand_rows = [r for r in rows if r.get("Brand") == b]
        brand_catalog = get_brand_catalog(b)
        brand_kws = get_brand_keywords(b)

        if not brand_rows:
            continue

        # -------------------------------
        # 1. BASIC METRICS
        # -------------------------------
        health_scores = [p.get("health_score", 50) for p in brand_catalog]

        avg_health = (
            sum(health_scores) / len(health_scores)
            if health_scores else 50
        )

        total_catalog = len(brand_catalog) if brand_catalog else 1

        missing_desc = (
            sum(1 for p in brand_catalog
                if (p.get("content_snapshot", {}).get("description_score", 0) < 50))
            / total_catalog
        ) * 100

        missing_media = (
            sum(1 for p in brand_catalog
                if (p.get("content_snapshot", {}).get("videos_score", 0) == 0))
            / total_catalog
        ) * 100

        missing_reviews = (
            sum(1 for p in brand_catalog
                if (p.get("content_snapshot", {}).get("reviews_score", 0) < 50))
            / total_catalog
        ) * 100

        # EXACT PHP: rand(5,15)
        oos_rate = random.randint(5, 15)  # noqa: S311

        anxiety = min(
            5.0,
            round(3.0 + (missing_reviews / 100 * 1.0) + (missing_media / 100 * 1.0), 1)
        )

        unrated = (
            sum(1 for p in brand_catalog
                if (p.get("detail_data", {}).get("reviews", 0) == 0))
            / total_catalog
        ) * 100

        # -------------------------------
        # 2. SEO BLINDSPOTS (LOWEST PRESENCE)
        # -------------------------------
        blindspots = []

        if brand_kws:
            # PHP: uasort ascending by presence ratio
            sorted_kws = sorted(
                brand_kws.items(),
                key=lambda x: (x[1]["present"] / x[1]["total"])
                if x[1]["total"] > 0 else 0
            )

            top_kws = sorted_kws[:10]

            for kw, stats in top_kws:
                presence = (stats["present"] / stats["total"]) * 100 if stats["total"] else 0
                blindspots.append({
                    "keyword": kw,
                    "deficit": round(100 - presence)
                })
        else:
            # EXACT PHP fallback
            blindspots = [
                {"keyword": "Premium Design", "deficit": 90},
                {"keyword": "Fast Charging", "deficit": 85},
                {"keyword": "AI Camera", "deficit": 95},
            ]

        # -------------------------------
        # FINAL OBJECT
        # -------------------------------
        all_brand_stats[b] = {
            "anxiety": anxiety,
            "missing_descriptions": round(missing_desc),
            "missing_media": round(missing_media),
            "missing_reviews": round(missing_reviews),
            "oos_rate": round(oos_rate),
            "health_score": round(avg_health),
            "unrated_listings": round(unrated),
            "premium_health_drop": random.randint(10, 30),  # EXACT PHP  # noqa: S311
            "description_coverage": round(100 - missing_desc),
            "media_coverage": round(100 - missing_media),
            "review_coverage": round(100 - missing_reviews),
            "share": (len(brand_rows) / total_listing_count) * 100,
            "keywords": blindspots
        }

    # ===============================
    # 3. RANKING (DESC by share)
    # ===============================
    sorted_brands = sorted(
        all_brand_stats.items(),
        key=lambda x: x[1]["share"],
        reverse=True
    )

    ranked_stats = {}
    rank = 1

    for brand_name, stats in sorted_brands:
        stats["share_rank"] = rank
        ranked_stats[brand_name] = stats
        rank += 1

    # ===============================
    # 4. BENCHMARK (AVERAGES)
    # ===============================
    values = list(ranked_stats.values())
    count = len(values) or 1

    benchmark = {
        "anxiety": round(sum(v["anxiety"] for v in values) / count, 1),
        "health_score": round(sum(v["health_score"] for v in values) / count),
        "description_coverage": round(sum(v["description_coverage"] for v in values) / count),
        "media_coverage": round(sum(v["media_coverage"] for v in values) / count),
        "review_coverage": round(sum(v["review_coverage"] for v in values) / count),
    }

    output = {
        "brands": ranked_stats,
        "benchmark": benchmark,
        "last_updated": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


    # ===============================
    # 5. SAVE (your system)
    # ===============================
    file_name, file_path = save_or_update_region_json(
        region_id,
        template,
        output,
        current_brand,
        task
    )

    return True, {
        "file_name": file_name,
        "file_path": file_path,
        "success": True,
        "message": "Risk Dashboard Data successfully regenerated."
    }
