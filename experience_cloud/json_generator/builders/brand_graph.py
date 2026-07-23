from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import safe_float
from typing import Dict, List, Optional, Any, Union, Tuple
from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.utils import serve_region_template_json, save_or_update_region_json
import re

@handle_builder_exceptions
def brand_graph_builder(region_data: RegionDataSchema, task, products=None, template="template-name") -> tuple[bool, dict]:
    region_id = region_data.get("region_id")
    current_brand = region_data.get("brand_name")
    brand_id = region_data.get("brand_id")
    
    # ===============================
    # 1. LOAD DATA
    # ===============================
    catalog_data = serve_region_template_json(
        region_id, "catalog-data-complete"
    )

    keyword_matrix = serve_region_template_json(
        region_id, "keyword-matrix"
    )

    if not catalog_data or not keyword_matrix:
        raise Exception(
            "Failed to load data files. Check if files exist and are valid JSON."
        )

    # ===============================
    # 2. INIT
    # ===============================
    brand_averages = keyword_matrix.get("summary", {}).get("brand_averages", {})
    brand_graph_results = []
    F = 0.3144  # EXACT same

    # ===============================
    # 3. LOOP (exact PHP logic)
    # ===============================
    for brand_name, products_list in catalog_data.items():

        if not isinstance(products_list, list):
            continue

        m_score = brand_averages.get(brand_name, 0)

        total_health_score = 0
        total_incentive = 0
        total_anxiety = 0
        product_count = 0

        for product in products_list:
            product_count += 1

            # -------------------------------
            # V: Health Score
            # -------------------------------
            total_health_score += product.get("health_score", 0)

            # -------------------------------
            # I: Incentive
            # -------------------------------
            msrp = safe_float(product.get("msrp", 0) or 0)

            sell_price = safe_float(
                product.get("detail_data", {}).get("sell_price", 0) or 0
            )

            if msrp > 0:
                total_incentive += ((msrp - sell_price) / msrp) * 100

            # -------------------------------
            # A: Anxiety (IMPORTANT parsing)
            # -------------------------------
            rating_str = str(
                product.get("detail_data", {}).get("rating", "0")
            )

            # PHP: preg_replace('/[^0-9.]/', '', $rating_str)
            rating_clean = re.sub(r"[^0-9.]", "", rating_str)
            rating = safe_float(rating_clean or 0)

            reviews = safe_float(
                product.get("detail_data", {}).get("reviews", 0) or 0
            )

            # EXACT FORMULA
            product_anxiety = (0.4 * rating + 0.6 * reviews) / 2
            total_anxiety += product_anxiety

        # ===============================
        # 4. CALCULATE FINAL METRICS
        # ===============================
        if product_count > 0:

            V = total_health_score / product_count
            I = total_incentive / product_count
            A = total_anxiety / product_count
            M = m_score

            # EXACT PHP LOGIC
            if M > 33:
                M = 32.5

            # C = 4M + 3V + 2(I - F) - 2A
            C = (4 * (33 - M)) + (3 * V) + (2 * (I - F)) - (2 * A)

            brand_graph_results.append({
                "Brand": brand_name,
                "M": round((100 - M), 2),   # EXACT
                "V": round(V, 2),
                "I": round(I, 2),
                "F": F,
                "A": round(A, 2),
                "C": round(C, 4)
            })

    # ===============================
    # 5. SAVE
    # ===============================
    file_name, file_path = save_or_update_region_json(
        region_id,
        template,
        brand_graph_results,
        current_brand,
        task
    )

    return True, {
        "file_name": file_name,
        "file_path": file_path,
        "success": True,
        "message": "Brand Graph successfully generated and saved."
    }
