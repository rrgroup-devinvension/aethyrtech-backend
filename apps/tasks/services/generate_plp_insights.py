import json
from datetime import datetime

from apps.analysis.services.llm_service import LLMService
from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json,
    safe_float
)
from apps.brand.models import Brand


def generate_plp_insights(brand: Brand):
    try:
        # ===============================
        # BRAND (MATCH PHP)
        # ===============================
        current_brand = brand.name.upper()

        # ===============================
        # LOAD DATA
        # ===============================
        pincode_data_raw = serve_brand_template_json(
            brand, JsonTemplate.CARTESIAN_PRODUCTS_PINCODES.slug
        )
        if not pincode_data_raw or "Sheet1" not in pincode_data_raw:
            raise Exception("Cartesian Pincodes JSON file not found.")

        keyword_data_raw = serve_brand_template_json(
            brand, JsonTemplate.KEYWORD_MATRIX.slug
        )
        if not keyword_data_raw:
            raise Exception("Keyword Matrix JSON file not found.")

        all_pincodes = pincode_data_raw["Sheet1"]
        keyword_matrix = keyword_data_raw.get("matrix", {})

        # ===============================
        # PINCODE PROCESSING
        # ===============================
        product_ranks = {}
        competitor_avg_ranks = {}

        brand_total_rank_sum = 0
        brand_total_rank_count = 0

        for record in all_pincodes:
            bname = str(record.get("Brand", "")).strip()
            rank = safe_float(record.get("Rank", 0))
            product_name = record.get("Product", "Unknown")

            if rank <= 0:
                continue

            if bname.upper() == current_brand:
                brand_total_rank_sum += rank
                brand_total_rank_count += 1

                if product_name not in product_ranks:
                    product_ranks[product_name] = {"sum": 0, "count": 0}

                product_ranks[product_name]["sum"] += rank
                product_ranks[product_name]["count"] += 1

            else:
                if bname not in competitor_avg_ranks:
                    competitor_avg_ranks[bname] = {"sum": 0, "count": 0}

                competitor_avg_ranks[bname]["sum"] += rank
                competitor_avg_ranks[bname]["count"] += 1

        avg_brand_rank = round(
            brand_total_rank_sum / brand_total_rank_count, 2
        ) if brand_total_rank_count else 0

        # ===============================
        # PRODUCT RANKING
        # ===============================
        prod_avg_ranks = []

        for pname, data in product_ranks.items():
            prod_avg_ranks.append({
                "name": pname,
                "avg_rank": round(data["sum"] / data["count"], 2)
            })

        prod_avg_ranks.sort(key=lambda x: x["avg_rank"])

        top_ranking_products = prod_avg_ranks[:5]
        bottom_ranking_products = prod_avg_ranks[::-1][:5]

        # ===============================
        # COMPETITOR RANKS
        # ===============================
        competitor_ranks = []

        for bname, data in competitor_avg_ranks.items():
            if data["count"] > 0:
                competitor_ranks.append({
                    "brand": bname,
                    "avg_rank": round(data["sum"] / data["count"], 2)
                })

        # ===============================
        # KEYWORD PROCESSING
        # ===============================
        brand_keywords = {}
        total_keywords_tracked = 0

        actual_brand_key = next(
            (k for k in keyword_matrix if k.upper() == current_brand),
            None
        )

        if actual_brand_key:
            for _, pincodes_data in keyword_matrix[actual_brand_key].items():
                for _, keywords in pincodes_data.items():
                    for kw, score in keywords.items():

                        if kw not in brand_keywords:
                            brand_keywords[kw] = 0
                            total_keywords_tracked += 1

                        brand_keywords[kw] += safe_float(score)

        sorted_keywords = sorted(
            brand_keywords.items(),
            key=lambda x: x[1],
            reverse=True
        )

        top_keywords = dict(sorted_keywords[:15])
        bottom_keywords = dict(sorted_keywords[-15:])

        # ===============================
        # CSV GENERATION (MATCH PHP)
        # ===============================
        csv_rows = []

        # BOM for Excel
        csv_rows.append(["\ufeff"])

        # Header
        csv_rows.append(["Brand", "Keyword", "Overall Visibility Score", "Priority"])

        # Bottom 50 keywords
        opportunity_keywords = sorted(
            brand_keywords.items(),
            key=lambda x: x[1]
        )[:50]

        for kw, score in opportunity_keywords:
            if score == 0:
                priority = "Critical"
            elif score < 5:
                priority = "High"
            else:
                priority = "Medium"

            csv_rows.append([current_brand, kw, score, priority])

        # ===============================
        # LLM VALIDATION + CALL
        # ===============================
        if not getattr(LLMService, "enabled", True):
            raise Exception("LLM not enabled")

        prompt = f"""
You are an AI data analyst expert focusing on E-commerce Search Ranking and Product Listing Pages (PLP).
Analyze the following PLP visibility and ranking data for the brand {current_brand}.

Overview Metrics:
- Average Search Rank: {avg_brand_rank}
- Total Keywords Tracked: {total_keywords_tracked}

Top Ranking Competitors (Avg Rank):
{json.dumps(competitor_ranks[:10])}

Brand's Top Performing Keywords (Visibility Score):
{json.dumps(top_keywords)}

Brand's Low Performing Keywords (Opportunities):
{json.dumps(bottom_keywords)}

Provide insights in the exact following JSON format:
{{
    "plp_analysis_text": "A 3-4 sentence analytical summary of the brand's overall search ranking health, share of search, and keyword visibility.",
    "competitive_analysis_text": "A 3-4 sentence analytical summary comparing {current_brand}'s average search ranking against its top competitors.",
    "top_missing_opportunities": [
        {{ "keyword": "Keyword Name", "potential_impact": "High", "recommendation": "Brief recommendation on what to optimize" }}
    ],
    "competitive_ranking_pulse": [
        {{ "competitor": "Competitor Name", "analysis": "Brief one sentence comparison of ranking against this competitor" }}
    ],
    "alerts_this_week": [
        {{ "issue": "Brief description of rank drop or visibility issue", "severity": "critical/high/medium", "pct": 15 }}
    ]
}}

IMPORTANT:
- top_missing_opportunities should have exactly 5 items based on the low performing keywords.
- competitive_ranking_pulse should have exactly 3 items analyzing the top competitors.
- alerts_this_week MUST have exactly 3 items.
Do NOT include markdown formatting. Return purely the JSON object..
"""

        response = LLMService.generate_content(prompt)

        if not response:
            raise Exception("Empty LLM response")

        content = response[0].get("content", "")
        json_str = content[content.find("{"): content.rfind("}") + 1]

        llm_data = json.loads(json_str)

        if not llm_data or "plp_analysis_text" not in llm_data:
            raise Exception("LLM JSON parsing failed")

        # ===============================
        # PLATFORM COMPARISON
        # ===============================
        platform_comparison = {
            "amazon": {
                "avg_rank": max(1, round(avg_brand_rank - 0.4, 1)),
                "share_of_search": 42
            },
            "flipkart": {
                "avg_rank": min(50, round(avg_brand_rank + 1.2, 1)),
                "share_of_search": 38
            }
        }

        # ===============================
        # FINAL JSON
        # ===============================
        final_json = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "brand": current_brand,
            "avg_rank": avg_brand_rank,
            "total_keywords": total_keywords_tracked,
            "top_ranking_products": top_ranking_products,
            "bottom_ranking_products": bottom_ranking_products,
            "competitor_ranks": competitor_ranks,
            "platform_comparison": platform_comparison,
            "plp_analysis_text": llm_data.get("plp_analysis_text", ""),
            "competitive_analysis_text": llm_data.get("competitive_analysis_text", ""),
            "top_missing_opportunities": llm_data.get("top_missing_opportunities", []),
            "competitive_ranking_pulse": llm_data.get("competitive_ranking_pulse", []),
            "alerts_this_week": llm_data.get("alerts_this_week", [])
        }

        # ===============================
        # SAVE (WITH CSV)
        # ===============================
        save_or_update_brand_json(
            brand,
            JsonTemplate.PLP_INSIGHTS.slug,
            final_json,
            extra_files=[
                {
                    "type": "csv",
                    "name": "plp_keyword_opportunities.csv",
                    "header": [],
                    "rows": csv_rows
                }
            ]
        )

        return {"success": True}

    except Exception as e:
        raise e