import json
from datetime import datetime

from apps.analysis.services.llm_service import LLMService
from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json, safe_float
)
from apps.brand.models import Brand


def generate_plp_insights(brand: Brand):

    current_brand = brand.name

    # ===============================
    # LOAD DATA
    # ===============================
    pincode_data_raw = serve_brand_template_json(
        brand, JsonTemplate.CARTESIAN_PRODUCTS_PINCODES.slug
    )

    keyword_data_raw = serve_brand_template_json(
        brand, JsonTemplate.KEYWORD_MATRIX.slug
    )

    if not pincode_data_raw or "Sheet1" not in pincode_data_raw:
        raise Exception("Invalid Cartesian Pincodes JSON format.")

    all_pincodes = pincode_data_raw["Sheet1"]
    keyword_matrix = keyword_data_raw.get("matrix", {})

    # ===============================
    # PINCODE PROCESSING
    # ===============================
    brand_records = []
    competitor_avg_ranks = {}

    product_ranks = {}
    brand_total_rank_sum = 0
    brand_total_rank_count = 0

    for record in all_pincodes:
        bname = record.get("Brand", "Unknown")
        rank = safe_float(record.get("Rank", 0))
        product_name = record.get("Product", "Unknown")

        if rank <= 0:
            continue

        if bname.lower() == current_brand.lower():

            brand_records.append(record)
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
        avg_rank = round(data["sum"] / data["count"], 2)
        prod_avg_ranks.append({"name": pname, "avg_rank": avg_rank})

    prod_avg_ranks.sort(key=lambda x: x["avg_rank"])

    top_ranking_products = prod_avg_ranks[:5]
    bottom_ranking_products = list(reversed(prod_avg_ranks))[:5]

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

    actual_brand_key = None
    for key in keyword_matrix.keys():
        if key.lower() == current_brand.lower():
            actual_brand_key = key
            break

    if actual_brand_key and actual_brand_key in keyword_matrix:

        for _, pincodes_data in keyword_matrix[actual_brand_key].items():
            for _, keywords in pincodes_data.items():
                for kw, score in keywords.items():

                    if kw not in brand_keywords:
                        brand_keywords[kw] = 0
                        total_keywords_tracked += 1

                    brand_keywords[kw] += score

    # SORT KEYWORDS
    sorted_keywords = dict(
        sorted(brand_keywords.items(), key=lambda x: x[1], reverse=True)
    )

    top_keywords = dict(list(sorted_keywords.items())[:15])
    bottom_keywords = dict(list(sorted_keywords.items())[-15:])

    # ===============================
    # LLM INPUT PREP
    # ===============================
    competitor_ranks_json = json.dumps(competitor_ranks[:10])
    top_kw_json = json.dumps(top_keywords)
    bottom_kw_json = json.dumps(bottom_keywords)

    # ===============================
    # EXACT PROMPT (NO CHANGE)
    # ===============================
    prompt = f"""
You are an AI data analyst expert focusing on E-commerce Search Ranking and Product Listing Pages (PLP).
Analyze the following PLP visibility and ranking data for the brand {current_brand}.

Overview Metrics:
- Average Search Rank: {avg_brand_rank}
- Total Keywords Tracked: {total_keywords_tracked}

Top Ranking Competitors (Avg Rank):
{competitor_ranks_json}

Brand's Top Performing Keywords (Visibility Score):
{top_kw_json}

Brand's Low Performing Keywords (Opportunities):
{bottom_kw_json}

Provide insights in the exact following JSON format:
{{
    "plp_analysis_text": "",
    "competitive_analysis_text": "",
    "top_missing_opportunities": [],
    "competitive_ranking_pulse": [],
    "alerts_this_week": []
}}

IMPORTANT:
- top_missing_opportunities should have exactly 5 items.
- competitive_ranking_pulse should have exactly 3 items.
- alerts_this_week MUST have exactly 3 items.
Do NOT include markdown formatting. Return purely JSON.
"""

    response = LLMService.generate_content(prompt)

    if not response:
        raise Exception("Empty LLM response")
    content = response[0].get("content", "")
    start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end == -1:
        raise Exception("Invalid JSON response from LLM")

    llm_data = json.loads(content[start:end])

    # ===============================
    # PLATFORM MOCK (SAME AS PHP)
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
    # SAVE
    # ===============================
    save_or_update_brand_json(
        brand,
        JsonTemplate.PLP_INSIGHTS.slug,
        final_json
    )

    return {
        "message": "PLP Insights generated successfully"
    }