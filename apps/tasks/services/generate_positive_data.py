from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json
)
from apps.brand.models import Brand
import random


def generate_positive_data(brand: Brand):
    try:
        # ===============================
        # 1. LOAD DATA (same as PHP)
        # ===============================
        try:
            pincode_data = serve_brand_template_json(
                brand, JsonTemplate.CARTESIAN_PRODUCTS_PINCODES.slug
            )
        except Exception:
            raise Exception("Failed to load pincode data")

        try:
            catalog_data = serve_brand_template_json(
                brand, JsonTemplate.CATALOG.slug
            )
        except Exception:
            raise Exception("Failed to load catalog data")

        keyword_data = serve_brand_template_json(
            brand, JsonTemplate.KEYWORD_COUNTS.slug
        )

        # ===============================
        # VALIDATION
        # ===============================
        if "Sheet1" not in pincode_data:
            raise Exception("cartesian_products_pincodes.json missing 'Sheet1' key.")

        rows = pincode_data["Sheet1"]

        brands = list(set([r.get("Brand") for r in rows if r.get("Brand")]))
        total_listing_count = len(rows)

        total_pins = len(set([r.get("Pincode") for r in rows if r.get("Pincode")]))

        all_brand_stats = {}

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
            # 1. CORE METRICS
            # -------------------------------
            share = (len(brand_rows) / total_listing_count) * 100

            avg_price = sum(r.get("Current Price (₹)", 0) for r in brand_rows) / len(brand_rows)

            brand_pins = len(set([r.get("Pincode") for r in brand_rows]))
            coverage = (brand_pins / total_pins) * 100 if total_pins else 0

            avg_rating = sum(r.get("Rating", 0) for r in brand_rows) / len(brand_rows)

            health_scores = [p.get("health_score", 50) for p in brand_catalog]
            avg_health = sum(health_scores) / len(health_scores) if health_scores else 50

            # -------------------------------
            # 2. ANXIETY + CONVERSION
            # -------------------------------
            total_cat = len(brand_catalog) if brand_catalog else 1

            missing_media = (
                sum(1 for p in brand_catalog
                    if (p.get("content_snapshot", {}).get("videos_score", 0) == 0))
                / total_cat
            ) * 100

            missing_reviews = (
                sum(1 for p in brand_catalog
                    if (p.get("content_snapshot", {}).get("reviews_score", 0) < 50))
                / total_cat
            ) * 100

            anxiety = min(
                5.0,
                round(3.0 + (missing_reviews / 100 * 1.0) + (missing_media / 100 * 1.0), 1)
            )

            # EXACT PHP FORMULA
            conversion = round(
                250 + (avg_rating * 20) - (anxiety * 10) + random.randint(0, 50),
                1
            )

            # -------------------------------
            # 3. SEO OPPORTUNITIES (DESC)
            # -------------------------------
            opportunities = []

            if brand_kws:
                sorted_kws = sorted(
                    brand_kws.items(),
                    key=lambda x: (x[1]["present"] / x[1]["total"])
                    if x[1]["total"] > 0 else 0,
                    reverse=True
                )

                top_kws = sorted_kws[:10]

                for kw, stats in top_kws:
                    presence = (
                        (stats["present"] / stats["total"]) * 100
                        if stats["total"] else 0
                    )

                    opportunities.append({
                        "keyword": kw,
                        "presence": round(presence)
                    })

            # -------------------------------
            # FINAL OBJECT
            # -------------------------------
            all_brand_stats[b] = {
                "conversion": conversion,
                "share": round(share, 1),
                "price": round(avg_price),
                "coverage": round(coverage),
                "anxiety": anxiety,
                "health": round(avg_health),
                "rating": round(avg_rating, 1),
                "incentive_efficiency": -11.7 + (random.randint(-20, 20) / 10),
                "incentive_status": "Conversion Bonus",
                "keywords": opportunities
            }

        # ===============================
        # 3. RANKING
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
        # 4. MARKET AVERAGE
        # ===============================
        values = list(ranked_stats.values())

        market_avg = {
            "conversion": round(sum(v["conversion"] for v in values) / len(values), 1),
            "share": round(sum(v["share"] for v in values) / len(values), 1),
            "price": round(sum(v["price"] for v in values) / len(values)),
            "health": round(sum(v["health"] for v in values) / len(values)),
            "anxiety": round(sum(v["anxiety"] for v in values) / len(values), 1),
            "incentive_efficiency": round(
                sum(v["incentive_efficiency"] for v in values) / len(values),
                1
            ),
        }

        output = {
            "brands": ranked_stats,
            "marketAvg": market_avg
        }

        # ===============================
        # 5. SAVE
        # ===============================
        save_or_update_brand_json(
            brand,
            JsonTemplate.POSITIVE_DATA.slug,
            output
        )

        return {
            "success": True,
            "message": "Positive Dashboard Data successfully regenerated."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }