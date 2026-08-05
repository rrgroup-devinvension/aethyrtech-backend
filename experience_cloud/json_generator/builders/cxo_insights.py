from experience_cloud.json_generator.models import TemplateCodes
import json

from core.llm_providers.services.llm_service import LLMService
from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import save_or_update_region_json, serve_region_template


@handle_builder_exceptions
def cxo_insights_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Synthesize cross-functional catalog, keyword, and logistical data to generate CXO-level strategic insights.

    Compiles fragmented market data payloads and orchestrates a highly contextualized prompt to the LLM,
    returning deeply personalized, actionable insights structured for executive consumption.
    """
    current_brand = region_data.get("brand_name")
    assert current_brand is not None
    brand_id = region_data.get("brand_id")


    region_id = region_data.get("region_id")
    assert region_id is not None

    # ===============================
    # LOAD REQUIRED DATA
    # ===============================
    brand_graph = serve_region_template(
        region_id, TemplateCodes.BRAND_GRAPH.value
    )

    keyword_counts = serve_region_template(
        region_id, TemplateCodes.KEYWORD_COUNTS.value
    )

    pincode_data = serve_region_template(
        region_id, TemplateCodes.CARTESIAN_PRODUCTS_PINCODES.value
    )

    # ===============================
    # VALIDATION (MATCH PHP)
    # ===============================
    missing = []

    if not brand_graph:
        missing.append(TemplateCodes.BRAND_GRAPH.value)

    if not keyword_counts:
        missing.append(TemplateCodes.KEYWORD_COUNTS.value)

    if not pincode_data:
        missing.append("pincodes")

    if missing:
        raise ValueError(
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
                {r.get("Pincode") for r in brand_records}
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

2. LOGISTICS, COVERAGE & PRICING (pincodes):
(Summary and sample for {current_brand})
{brand_pincode_summary}

3. SEO COVERAGE (keyword-counts.json):
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
            "type": "positive\" OR \"negative",
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
    response = LLMService.get_service().generate_content(
        [
            {'role': 'system', 'content': 'Extract high-level executive insights from raw e-commerce data.'},
            {'role': 'user', 'content': prompt}
        ], action="cxo_insights",
        brand_id=brand_id, brand_name=current_brand
    )
    start = response.find("{")
    end = response.rfind("}") + 1
    if start == -1 or end == -1:
        raise ValueError("Invalid JSON response from LLM")

    llm_data = json.loads(response[start:end])

    if not llm_data or "cxo_insights" not in llm_data:
        raise ValueError("JSON Parsing Failed")

    # ===============================
    # SAVE
    # ===============================
    file_name, file_path = save_or_update_region_json(
        region_id,
        template,
        llm_data,
        current_brand,
        task
    )

    return False, llm_data
