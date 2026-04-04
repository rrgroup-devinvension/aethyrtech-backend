from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json
)
from apps.brand.models import Brand
from datetime import datetime
import random


def generate_positive_data(brand: Brand):
    try:
        # ===============================
        # 1. LOAD DATA (WITH FALLBACK)
        # ===============================
        try:
            pincode_data = serve_brand_template_json(
                brand, JsonTemplate.CARTESIAN_PRODUCTS_PINCODES.slug
            )
        except Exception:
            pincode_data = {"Sheet1": []}

        try:
            catalog_data = serve_brand_template_json(
                brand, JsonTemplate.CATALOG.slug
            )
        except Exception:
            catalog_data = {"Sheet1": []}

        try:
            keyword_data = serve_brand_template_json(
                brand, JsonTemplate.KEYWORD_COUNTS.slug
            )
        except Exception:
            keyword_data = {"Sheet1": []}

        # ===============================
        # 2. VALIDATION
        # ===============================
        if "Sheet1" not in pincode_data:
            raise Exception("cartesian_products_pincodes.json missing 'Sheet1' key.")

        rows = pincode_data["Sheet1"]

        # Avoid division by zero
        total_listing_count = len(rows) or 1

        # Preserve order like PHP array_unique
        brands = list(dict.fromkeys(
            r.get("Brand") for r in rows if r.get("Brand")
        ))

        # IMPORTANT: match PHP behavior (include nulls also)
        total_pins = len(set(r.get("Pincode") for r in rows))

        all_brand_stats = {}

        # ===============================
        # HELPERS
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
        # 3. MAIN LOOP
        # ===============================
        for b in brands:

            brand_rows = [r for r in rows if r.get("Brand") == b]
            if not brand_rows:
                continue

            brand_catalog = get_brand_catalog(b)
            brand_kws = get_brand_keywords(b)

            # -------------------------------
            # CORE METRICS
            # -------------------------------
            share = (len(brand_rows) / total_listing_count) * 100

            # Match PHP behavior: ignore missing values
            prices = [r["Current Price (₹)"] for r in brand_rows if "Current Price (₹)" in r]
            avg_price = (sum(prices) / len(prices)) if prices else 0

            ratings = [r["Rating"] for r in brand_rows if "Rating" in r]
            avg_rating = (sum(ratings) / len(ratings)) if ratings else 0

            brand_pins = len(set(r.get("Pincode") for r in brand_rows))
            coverage = (brand_pins / total_pins) * 100 if total_pins else 0

            health_scores = [p.get("health_score") for p in brand_catalog if "health_score" in p]
            avg_health = (sum(health_scores) / len(health_scores)) if health_scores else 50

            # -------------------------------
            # ANXIETY + CONVERSION
            # -------------------------------
            total_cat = len(brand_catalog) or 1

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
                round(3.0 + (missing_reviews / 100) + (missing_media / 100), 1)
            )

            conversion = round(
                250 + (avg_rating * 20) - (anxiety * 10) + random.randint(0, 50),
                1
            )

            # -------------------------------
            # SEO OPPORTUNITIES
            # -------------------------------
            opportunities = []

            if brand_kws:
                sorted_kws = sorted(
                    brand_kws.items(),
                    key=lambda x: (x[1]["present"] / x[1]["total"])
                    if x[1]["total"] > 0 else 0,
                    reverse=True
                )

                for kw, stats in sorted_kws[:10]:
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
        # 4. RANKING
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

        values = list(ranked_stats.values())

        if not values:
            raise Exception("No brand stats generated")

        # ===============================
        # 5. MARKET AVERAGE
        # ===============================
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

        # ===============================
        # 6. FINAL OUTPUT
        # ===============================
        output = {
            "brands": ranked_stats,
            "marketAvg": market_avg,
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # ===============================
        # 7. SAVE
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
        raise e