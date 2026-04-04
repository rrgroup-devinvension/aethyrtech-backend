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


def generate_pdp_insights(brand: Brand):
    try:
        # ===============================
        # BRAND (MATCH PHP)
        # ===============================
        current_brand = brand.name.upper()

        # ===============================
        # LOAD CATALOG DATA
        # ===============================
        catalog_data_raw = serve_brand_template_json(
            brand, JsonTemplate.CATALOG.slug
        )

        if not catalog_data_raw:
            raise Exception("Catalog JSON file not found.")

        # ===============================
        # FIND BRAND KEY (CASE-INSENSITIVE)
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
        # PRE-PROCESS
        # ===============================
        total_products = 0
        total_health_score = 0
        total_images = 0
        products_with_video = 0

        content_scores = {
            "title": 0,
            "description": 0,
            "bullets": 0,
            "images": 0
        }

        product_health_list = []
        pdps_needing_improvement = []

        for p in products:
            total_products += 1

            health = safe_float(p.get("health_score", 0))
            total_health_score += health

            detail = p.get("detail_data", {})
            snap = p.get("content_snapshot", {})

            img_count = int(detail.get("images", 0))
            total_images += img_count

            if int(detail.get("videos", 0)) > 0:
                products_with_video += 1

            content_scores["title"] += int(snap.get("title_score", 0))
            content_scores["description"] += int(snap.get("description_score", 0))
            content_scores["bullets"] += int(snap.get("bullets_score", 0))
            content_scores["images"] += int(snap.get("images_score", 0))

            product_title = p.get("product_title", "Unknown Product")

            product_health_list.append({
                "name": product_title,
                "health_score": health,
                "sku": p.get("sku", ""),
                "images": img_count
            })

            # LOW HEALTH PDPs
            if health < 40:
                missings = []

                if int(snap.get("title_score", 0)) < 50:
                    missings.append("Title Match/Length")

                if int(snap.get("description_score", 0)) < 50:
                    missings.append("Description")

                if int(snap.get("bullets_score", 0)) < 50:
                    missings.append("Bullets")

                if int(snap.get("images_score", 0)) < 50:
                    missings.append("Images (<5)")

                pdps_needing_improvement.append({
                    "sku": p.get("sku", ""),
                    "name": product_title,
                    "health_score": health,
                    "deficiencies": ", ".join(missings)
                })

        # ===============================
        # METRICS
        # ===============================
        avg_health_score = round(
            total_health_score / total_products, 1
        ) if total_products else 0

        avg_image_count = round(
            total_images / total_products, 1
        ) if total_products else 0

        video_penetration_pct = round(
            (products_with_video / total_products) * 100, 1
        ) if total_products else 0

        for k in content_scores:
            content_scores[k] = round(
                content_scores[k] / total_products, 1
            ) if total_products else 0

        # ===============================
        # SORT PRODUCTS
        # ===============================
        product_health_list.sort(
            key=lambda x: x["health_score"],
            reverse=True
        )

        top_pdps = product_health_list[:5]
        bottom_pdps = list(reversed(product_health_list))[:5]

        # ===============================
        # COMPETITOR METRICS
        # ===============================
        competitor_metrics = {}

        for b_key, b_products in catalog_data_raw.items():
            c_total = 0
            c_health = 0
            c_images = 0
            c_videos = 0

            for cp in b_products:
                c_total += 1
                c_health += safe_float(cp.get("health_score", 0))
                c_images += int(cp.get("detail_data", {}).get("images", 0))

                if int(cp.get("detail_data", {}).get("videos", 0)) > 0:
                    c_videos += 1

            if c_total > 0:
                competitor_metrics[b_key.strip()] = {
                    "total_products": c_total,
                    "avg_health_score": round(c_health / c_total, 1),
                    "avg_image_count": round(c_images / c_total, 1),
                    "video_penetration_pct": round((c_videos / c_total) * 100, 1)
                }

        # ===============================
        # CSV: PDP CONTENT AUDIT (MATCH PHP)
        # ===============================
        csv_rows = []

        # BOM for Excel
        csv_rows.append(["\ufeff"])

        # Header
        csv_rows.append([
            "Brand",
            "SKU",
            "Product Title",
            "Overall Health Score",
            "Deficiencies / Missing Content"
        ])

        for issue in pdps_needing_improvement:
            csv_rows.append([
                current_brand,
                issue["sku"],
                issue["name"],
                issue["health_score"],
                issue["deficiencies"]
            ])

        # ===============================
        # LLM VALIDATION + CALL
        # ===============================
        if not getattr(LLMService, "enabled", True):
            raise Exception("LLM not enabled")

        audit_sample = json.dumps(pdps_needing_improvement[:15])
        comp_sample = json.dumps(competitor_metrics)

        prompt = f"""
You are an AI data analyst expert focusing on E-commerce Product Detail Page (PDP) Content Optimization, Value Proposition, and Competitive Intelligence.
Analyze the following PDP health metrics for the brand {current_brand}.

Overview Metrics:
- Total Products Analyzed: {total_products}
- Average Catalog Health Score (out of 100): {avg_health_score}
- Average Images per Product: {avg_image_count}
- % Products with Video Content: {video_penetration_pct}%

Content Component Average Scores (Scale 0-100):
- Title Score: {content_scores['title']}
- Description Score: {content_scores['description']}
- Feature Bullets Score: {content_scores['bullets']}
- Images Readiness Score: {content_scores['images']}

Competitive Landscape (Market Averages):
{comp_sample}

Sample of PDPs Needing Improvement (Low Health Scores):
{audit_sample}

Provide insights in the exact following JSON format:
{{
    "pdp_analysis_text": "",
    "competitive_analysis_text": "",
    "content_audit_plan": [],
    "alerts_this_week": []
}}

IMPORTANT:
- content_audit_plan should have exactly 4 items.
- alerts_this_week MUST have exactly 3 items.
Do NOT include markdown formatting. Return purely JSON.
"""

        response = LLMService.generate_content(prompt)

        if not response:
            raise Exception("Empty LLM response")

        content = response[0].get("content", "")

        start = content.find("{")
        end = content.rfind("}")

        if start == -1 or end == -1:
            raise Exception("Invalid JSON response from LLM")

        llm_data = json.loads(content[start:end + 1])

        if not llm_data or "pdp_analysis_text" not in llm_data:
            raise Exception("LLM JSON parsing failed")

        # ===============================
        # FINAL JSON
        # ===============================
        final_json = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "brand": current_brand,
            "avg_health_score": avg_health_score,
            "total_products": total_products,
            "avg_image_count": avg_image_count,
            "video_penetration_pct": video_penetration_pct,
            "component_scores": content_scores,
            "top_pdps": top_pdps,
            "bottom_pdps": bottom_pdps,
            "competitor_metrics": competitor_metrics,
            "pdp_analysis_text": llm_data.get("pdp_analysis_text", ""),
            "competitive_analysis_text": llm_data.get("competitive_analysis_text", ""),
            "content_audit_plan": llm_data.get("content_audit_plan", []),
            "alerts_this_week": llm_data.get("alerts_this_week", [])
        }

        # ===============================
        # SAVE (WITH CSV)
        # ===============================
        save_or_update_brand_json(
            brand,
            JsonTemplate.PDP_INSIGHTS.slug,
            final_json,
            extra_files=[
                {
                    "type": "csv",
                    "name": "pdp_content_audit.csv",
                    "header": [],
                    "rows": csv_rows
                }
            ]
        )

        return {"success": True}

    except Exception as e:
        raise e