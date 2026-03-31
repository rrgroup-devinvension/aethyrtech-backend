import json
from datetime import datetime

from apps.analysis.services.llm_service import LLMService
from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json
)
from apps.brand.models import Brand


def generate_cxo_insights(brand: Brand):

    current_brand = brand.name

    # ===============================
    # LOAD REQUIRED DATA
    # ===============================
    brand_graph = serve_brand_template_json(
        brand, JsonTemplate.BRAND_GRAPH.slug
    )

    content_insights = {
        "audit_summary": {
            "section_title": "Audit Summary",
            "cards": [
            { "label": "Sites Audited", "value": 5 },
            { "label": "Pages Audited", "value": 0 },
            { "label": "Product Availability", "value": "0%" },
            { "label": "Live Audited", "value": "100%" },
            { "label": "Missing Pages", "value": "0%" },
            { "label": "Audit Errors", "value": "0%" },
            { "label": "Master vs Live", "value": "0%" },
            { "label": "Previous vs Live", "value": "0%" },
            { "label": "Flagged Issues", "value": 0 }
            ]
        },
        "summary_box": {
            "content": "Content audit data pending. Please run comprehensive content analysis to populate this section."
        },
        "overall_health_chart": {
            "section_title": "Overall Health Score",
            "your_score": 0,
            "scale": [
            { "min": 0, "max": 19, "label": "None" },
            { "min": 20, "max": 39, "label": "Poor" },
            { "min": 40, "max": 59, "label": "Needs Improvement" },
            { "min": 60, "max": 79, "label": "Average" },
            { "min": 80, "max": 99, "label": "Very Good" },
            { "min": 100, "max": 100, "label": "Best in Class" }
            ]
        },
        "recommended_actions": {
            "section_title": "Recommended Actions",
            "note": "Content audit pending - comprehensive insights will be available after content analysis is completed."
        },
        "core_content_analysis": {
            "section_title": "Core Content Analysis",
            "note": "Detailed analysis pending. Please run comprehensive content audit."
        }
        }


    keyword_counts = serve_brand_template_json(
        brand, JsonTemplate.KEYWORD_COUNTS.slug
    )

    pincode_data = serve_brand_template_json(
        brand, JsonTemplate.CARTESIAN_PRODUCTS_PINCODES.slug
    )

    # ===============================
    # VALIDATION (MATCH PHP)
    # ===============================
    missing = []

    if not brand_graph:
        missing.append("brand_graph")

    if not content_insights:
        missing.append("content_insights_data")

    if not keyword_counts:
        missing.append("keyword-counts")

    if not pincode_data:
        missing.append("pincodes")

    if missing:
        raise Exception(
            f"Missing required data files for {current_brand}: {', '.join(missing)}"
        )

    # ===============================
    # PINCODE SUMMARY (EXACT LOGIC)
    # ===============================
    brand_pincode_summary = f"Pincode data not found for {current_brand}"

    if "Sheet1" in pincode_data:

        all_records = pincode_data["Sheet1"]

        brand_records = [
            r for r in all_records
            if r.get("Brand", "").lower() == current_brand.lower()
        ]

        if brand_records:

            total_listings = len(brand_records)
            unique_pincodes = len(
                set([r.get("Pincode") for r in brand_records])
            )

            avg_rank = sum([(r.get("Rank") or 0) for r in brand_records]) / total_listings
            avg_rating = sum([(r.get("Rating") or 0) for r in brand_records]) / total_listings

            summary_obj = {
                "brand": current_brand,
                "total_pincode_listings": total_listings,
                "unique_pincodes_covered": unique_pincodes,
                "average_search_rank": round(avg_rank, 2),
                "average_rating": round(avg_rating, 2),
                "sample_records": brand_records[:5]
            }

            brand_pincode_summary = json.dumps(summary_obj, indent=2)

    # ===============================
    # PREP DATA STRINGS
    # ===============================
    brand_graph_str = json.dumps(brand_graph)
    content_insights_str = json.dumps(content_insights)

    keywords_str = json.dumps(keyword_counts)[:1000]

    # ===============================
    # EXACT PROMPT (NO CHANGE)
    # ===============================
    prompt = f"""
You are a Senior Data Scientist and Strategic Brand Consultant for {current_brand}. 
Your task is to analyze the provided raw data and generate EXACTLY 16 high-impact strategic insights for the CMO (Marketing) and CCO (Commerce/Operations).

### DATA CONTEXT:
1. BRAND PERFORMANCE (brand_graph.json):
{brand_graph_str}

2. CONTENT AUDIT (content_insights_data.json):
(Summarized focus on {current_brand} gaps vs Competitors)
{content_insights_str}

3. LOGISTICS, COVERAGE & PRICING (pincodes):
(Summary and sample for {current_brand})
{brand_pincode_summary}

4. SEO COVERAGE (keyword-counts.json):
(Summarized focus on {current_brand} keyword presence in title/desc/bullets)
{keywords_str}...

### OBJECTIVE:
Generate 16 insights (8 positive 'Growth Units', 8 negative 'Risk Units'). 
Balance ownership between CMO and CCO.
Keep descriptions concise (under 20 words).
Ensure insights are data-driven, highlighting specific metrics.

### OUTPUT FORMAT:
Return ONLY a JSON object. NO MARKDOWN. NO CODE BLOCKS. NO PREAMBLE.
Schema:
{{
    "cxo_insights": [
        {{
            "id": 1,
            "title": "Title",
            "metric": "Metric",
            "bench": "Bench",
            "type": "positive",
            "impact": "High",
            "owner": "CMO",
            "description": "Brief desc.",
            "data_points": {{"Key": "Val"}}
        }}
    ]
}}
"""

    # ===============================
    # CALL LLM
    # ===============================
    response = LLMService.generate_content(prompt)

    if not response:
        raise Exception("Empty LLM response")
    content = response[0].get("content", "")
    start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end == -1:
        raise Exception("Invalid JSON response from LLM")

    llm_data = json.loads(content[start:end])

    if not llm_data or "cxo_insights" not in llm_data:
        raise Exception("JSON Parsing Failed")

    # ===============================
    # SAVE
    # ===============================
    save_or_update_brand_json(
        brand,
        JsonTemplate.INSIGHTS.slug,
        llm_data
    )

    return {
        "message": "Insights successfully generated"
    }