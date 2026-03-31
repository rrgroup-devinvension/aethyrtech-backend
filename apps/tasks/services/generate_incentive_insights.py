import json
from datetime import datetime

from apps.analysis.services.llm_service import LLMService
from apps.scheduler.enums import JsonTemplate
from apps.tasks.services.gen_utils import (
    serve_brand_template_json,
    save_or_update_brand_json, safe_float
)
from apps.brand.models import Brand



def generate_incentive_insights(brand: Brand):

    current_brand = brand.name

    # ===============================
    # LOAD CATALOG DATA
    # ===============================
    catalog_data_raw = serve_brand_template_json(
        brand, JsonTemplate.CATALOG.slug
    )
    if not catalog_data_raw:
        raise Exception("Catalog JSON not found.")

    # ===============================
    # FIND BRAND KEY
    # ===============================
    actual_brand_key = None
    for key in catalog_data_raw.keys():
        if key.lower() == current_brand.lower():
            actual_brand_key = key
            break

    if not actual_brand_key:
        raise Exception(f"No catalog data found for brand: {current_brand}")

    products = catalog_data_raw[actual_brand_key]

    # ===============================
    # PRICING PROCESSING
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

        # OPPORTUNITIES (<5%)
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
    # SORT PRODUCTS
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
    # LLM INPUT
    # ===============================
    opps_sample = json.dumps(discount_opportunities[:15])
    comp_sample = json.dumps(competitor_metrics)

    # ===============================
    # EXACT PROMPT
    # ===============================
    prompt = f"""
You are an AI commerce analyst expert focusing on E-commerce Pricing Strategies, Incentives, and Competitive Benchmarking.
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

Provide insights in the exact following JSON format:
{{
    "incentive_analysis_text": "",
    "competitive_analysis_text": "",
    "pricing_strategy_plan": [],
    "alerts_this_week": []
}}

IMPORTANT:
- pricing_strategy_plan should have exactly 4 items mapped to discount tiers.
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
    save_or_update_brand_json(
        brand,
        JsonTemplate.INCENTIVE_INSIGHTS.slug,
        final_json
    )

    return {
        "message": "Incentive Insights generated successfully"
    }