from experience_cloud.json_generator.models import TemplateCodes
import json
from datetime import datetime

from core.llm_providers.services.llm_service import LLMService
from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import safe_float, save_or_update_region_json, serve_region_template


@handle_builder_exceptions
def incentive_insights_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Analyze catalog pricing data and market benchmarks to generate strategic incentive insights via LLM integration.

    Aggregates discount tiers, identifies uncompetitive pricing gaps, and orchestrates an LLM prompt
    to synthesize actionable pricing recommendations and alerts for executive leadership.
    """
    # ===============================
    # BRAND (MATCH PHP)
    # ===============================
    current_brand = region_data.get("brand_name")
    brand_id = region_data.get("brand_id")
    region_id = region_data.get("region_id")

    if not region_id or not current_brand:
        raise ValueError("Region ID and Brand Name are required.")

    # ===============================
    # LOAD DATA
    # ===============================
    catalog_data_raw = serve_region_template(
        region_id, TemplateCodes.CATALOG.value
    )
    if not catalog_data_raw:
        raise ValueError("Catalog JSON file not found.")

    # ===============================
    # FIND BRAND KEY
    # ===============================
    actual_brand_key = None
    for key in catalog_data_raw:
        if key.lower() == current_brand.lower():
            actual_brand_key = key
            break

    if not actual_brand_key:
        raise ValueError(f"No catalog data found for brand: {current_brand}")

    products = catalog_data_raw[actual_brand_key]

    # ===============================
    # PROCESS PRICING
    # ===============================
    total_products = 0
    total_discount_pct = 0
    products_with_discount = 0
    deep_discounts_count = 0
    no_discounts_count = 0

    discount_tiers = {
        "0%": 0,
        "1-10%": 0,
        "11-30%": 0,
        "31%+": 0
    }

    product_discount_list = []
    discount_opportunities = []

    for p in products:
        total_products += 1

        msrp = safe_float(p.get("msrp"))
        sell_price = safe_float(p.get("detail_data", {}).get("sell_price"))

        discount_pct = 0
        if msrp > 0 and sell_price > 0 and msrp > sell_price:
            discount_pct = round(((msrp - sell_price) / msrp) * 100, 1)

        total_discount_pct += discount_pct

        if discount_pct > 0:
            products_with_discount += 1

            if discount_pct > 30:
                deep_discounts_count += 1
                discount_tiers["31%+"] += 1
            elif discount_pct > 10:
                discount_tiers["11-30%"] += 1
            else:
                discount_tiers["1-10%"] += 1
        else:
            no_discounts_count += 1
            discount_tiers["0%"] += 1

        product_title = p.get("product_title", "Unknown Product")

        product_discount_list.append({
            "name": product_title,
            "sku": p.get("sku", ""),
            "msrp": msrp,
            "sell_price": sell_price,
            "discount_pct": discount_pct
        })

        if discount_pct < 5:
            discount_opportunities.append({
                "sku": p.get("sku", ""),
                "name": product_title,
                "msrp": msrp,
                "sell_price": sell_price,
                "discount_pct": discount_pct
            })

    # ===============================
    # METRICS
    # ===============================
    avg_discount_pct = round(
        total_discount_pct / total_products, 1
    ) if total_products else 0

    active_promotions_pct = round(
        (products_with_discount / total_products) * 100, 1
    ) if total_products else 0

    # ===============================
    # SORT
    # ===============================
    product_discount_list.sort(
        key=lambda x: x["discount_pct"],
        reverse=True
    )

    top_discounted = product_discount_list[:5]
    bottom_discounted = list(reversed(product_discount_list))[:5]

    # ===============================
    # COMPETITOR METRICS
    # ===============================
    competitor_metrics = {}

    for b_key, b_products in catalog_data_raw.items():
        c_total = 0
        c_discount_total = 0
        c_promos = 0

        for cp in b_products:
            c_total += 1

            c_msrp = safe_float(cp.get("msrp"))
            c_sell = safe_float(cp.get("detail_data", {}).get("sell_price"))

            if c_msrp > 0 and c_sell > 0 and c_msrp > c_sell:
                pct = ((c_msrp - c_sell) / c_msrp) * 100
                c_discount_total += pct
                c_promos += 1

        if c_total > 0:
            competitor_metrics[b_key.strip()] = {
                "total_products": c_total,
                "avg_discount_pct": round(c_discount_total / c_total, 1),
                "active_promotions_pct": round((c_promos / c_total) * 100, 1)
            }

    # ===============================
    # CSV PREP: Discount Opportunities
    # ===============================
    from typing import Any
    csv_rows: list[list[Any]] = []
    csv_rows.append(['Brand', 'SKU', 'Product Title', 'MSRP', 'Sell Price', 'Current Discount %'])
    
    for opp in discount_opportunities:
        csv_rows.append([
            current_brand, 
            opp.get("sku", ""), 
            opp.get("name", ""), 
            opp.get("msrp", 0), 
            opp.get("sell_price", 0), 
            opp.get("discount_pct", 0)
        ])

    # ===============================
    # LLM VALIDATION
    # ===============================
    if not getattr(LLMService, "enabled", True):
        raise ValueError("LLM not enabled")

    opps_sample = json.dumps(discount_opportunities[:15])
    comp_sample = json.dumps(competitor_metrics)

    prompt = f"""
You are an AI commerce analyst expert focusing on E-commerce Pricing Strategies, Incentives, \
and Competitive Benchmarking.

Analyze the following Discounting (Incentive) metrics for the brand {current_brand}.

Overview Metrics:
- Total Products Analyzed: {total_products}
- Average Catalog Discount %: {avg_discount_pct}%
- % Promotions Active (Any discount > 0%): {active_promotions_pct}%
- Products with Deep Discounts (>30% loss to MSRP): {deep_discounts_count}
- Products with No Discount (Selling at MSRP): {no_discounts_count}

Discount Tier Spread (Product Counts):
- 0% Discount: {discount_tiers['0%']}
- 1-10% Discount: {discount_tiers['1-10%']}
- 11-30% Discount: {discount_tiers['11-30%']}
- 31%+ Discount: {discount_tiers['31%+']}

Competitive Landscape (Market Averages):
{comp_sample}

Sample of Uncompetitive/MSRP Price Points (< 5% discount):
{opps_sample}

Return ONLY a valid JSON object in the exact structure below.

{{
    "incentive_analysis_text": "A 3-4 sentence analytical summary of the brand's overall \
pricing strategy and discount aggressiveness.",
    "competitive_analysis_text": "A 3-4 sentence analytical summary comparison of {current_brand}'s \
discounting strategy versus competitors based on average discount % and promotion activity.",
    "pricing_strategy_plan": [
        {{
            "tier": "0% Discount",
            "observation": "Brief observation about products with no discount",
            "recommendation": "Actionable pricing recommendation"
        }},
        {{
            "tier": "1-10% Discount",
            "observation": "Brief observation",
            "recommendation": "Actionable pricing recommendation"
        }},
        {{
            "tier": "11-30% Discount",
            "observation": "Brief observation",
            "recommendation": "Actionable pricing recommendation"
        }},
        {{
            "tier": "31%+ Discount",
            "observation": "Brief observation",
            "recommendation": "Actionable pricing recommendation"
        }}
    ],
    "alerts_this_week": [
        {{
            "issue": "Critical pricing issue",
            "severity": "critical",
            "pct": 0
        }},
        {{
            "issue": "High priority issue",
            "severity": "high",
            "pct": 0
        }},
        {{
            "issue": "Medium priority issue",
            "severity": "medium",
            "pct": 0
        }}
    ]
}}

STRICT RULES:
- Do NOT include any explanation, markdown, or extra text.
- Return ONLY valid JSON.
- pricing_strategy_plan MUST contain exactly 4 items.
- alerts_this_week MUST contain exactly 3 items.
- Keep all text concise, business-focused, and actionable.
- Ensure JSON is properly formatted and parsable.
"""
    response = LLMService.get_service().generate_content(
        [{'role': 'user', 'content': prompt}], action="incentive_insights",
        brand_id=brand_id, brand_name=current_brand
    )
    if not response:
        raise ValueError("Empty LLM response")

    content = str(response)
    from experience_cloud.json_generator.utils import safe_parse_llm_json
    llm_data = safe_parse_llm_json(content)

    if not llm_data or "incentive_analysis_text" not in llm_data:
        raise ValueError("LLM JSON parsing failed")

    # ===============================
    # FINAL JSON
    # ===============================
    final_json = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "brand": current_brand,
        "avg_discount_pct": avg_discount_pct,
        "total_products": total_products,
        "active_promotions_pct": active_promotions_pct,
        "deep_discounts_count": deep_discounts_count,
        "no_discounts_count": no_discounts_count,
        "discount_tiers": discount_tiers,
        "top_discounted": top_discounted,
        "bottom_discounted": bottom_discounted,
        "competitor_metrics": competitor_metrics,
        "incentive_analysis_text": llm_data.get("incentive_analysis_text", ""),
        "competitive_analysis_text": llm_data.get("competitive_analysis_text", ""),
        "pricing_strategy_plan": llm_data.get("pricing_strategy_plan", []),
        "alerts_this_week": llm_data.get("alerts_this_week", [])
    }

    # ===============================
    # SAVE
    # ===============================
    # Since orchestrator expects file_name, file_path to be returned if returning True.
    # The new standard handles True returns by doing exactly this.
    file_name, file_path = save_or_update_region_json(
        region_id,
        template,
        final_json,
        current_brand,
        task
    )

    save_or_update_region_json(
        region_id,
        TemplateCodes.DISCOUNT_OPPORTUNITIES.value,
        csv_rows,
        current_brand,
        task=None
    )

    return True, {
        "file_name": file_name,
        "file_path": file_path,
        "success": True,
        "message": "Incentive Insights and CSV discount opportunities successfully generated."
    }
