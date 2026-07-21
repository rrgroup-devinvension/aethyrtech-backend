from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.utils import ItemGenerator
import logging

from datetime import datetime
from collections import defaultdict
from experience_cloud.json_generator.utils import match_brand

logger = logging.getLogger(__name__)

def build_keyword_matrix(region_data: dict, products: ItemGenerator) -> dict:
    brands = region_data.get("brands", [])
    brand_name = region_data.get("brand_name")
    
    # Using distinct_keywords directly from region_data as per the new schema
    brand_keywords = region_data.get("distinct_keywords", [])
    if not brand_keywords:
        # Fallback just in case
        brand_keywords = region_data.get("display_keywords", [])
        
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    aggregate_bucket = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
    
    # Resolve brand_pincodes safely from region_data
    brand_pincodes = []
    pincode_map = region_data.get('pincodes', {})
    if isinstance(pincode_map, dict):
        for pins in pincode_map.values():
            brand_pincodes.extend(pins)
    brand_pincodes = list(set(brand_pincodes)) if brand_pincodes else ["000000"]

    for p in products:
        if not p.brand or not p.title or not p.uid:
            continue
            
        product_brand = str(p.brand).strip()
        matched_brand = None
        for b in brands:
            if match_brand(b, product_brand):
                matched_brand = b
                break
                
        if not matched_brand:
            continue
            
        brand = matched_brand
        title = str(p.title).strip()
        ranking_data = p.rankings or {}
        
        product_pincode = brand_pincodes
        if p.platform_type == "marketplace":
            product_pincode = ["000000"]
            
        for pincode in product_pincode:
            rank_entries = ranking_data.get(pincode, [])
            for entry in rank_entries:
                kw = entry.get("keyword")
                rank = entry.get("rank")
                if rank is not None:
                    try:
                        rank = int(rank)
                        if rank > 32:
                            rank = 0
                    except (ValueError, TypeError):
                        rank = 0
                if kw and rank is not None:
                    aggregate_bucket[brand][title][pincode][kw].append(rank) 

    for brand, titles in aggregate_bucket.items():
        for title, pincodes in titles.items():
            for pincode, keywords_map in pincodes.items():
                result[brand][title][pincode] = {
                    kw: 0 for kw in brand_keywords
                }
                for kw, ranks in keywords_map.items():
                    avg_rank = round(sum(ranks) / len(ranks), 2) if ranks else 0
                    result[brand][title][pincode][kw] = avg_rank
    return dict(result)

def build_rank_averages(keyword_matrix: dict) -> dict:
    product_averages = {}
    brand_averages = {}
    overall_sum = 0
    overall_count = 0
    
    for brand, products in keyword_matrix.items():
        brand_sum = 0
        brand_count = 0
        for product_title, pincodes in products.items():
            product_sum = 0
            product_count = 0
            for pincode, keyword_ranks in pincodes.items():
                for kw, rank in keyword_ranks.items():
                    if rank and rank > 0:
                        product_sum += rank
                        product_count += 1
                        
            # Weighted Product Average
            if product_count > 0:
                avg_product_rank = round(product_sum / product_count, 2)
            else:
                avg_product_rank = 0
                
            product_averages[product_title] = avg_product_rank
            brand_sum += product_sum
            brand_count += product_count
            
        if brand_count > 0:
            avg_brand_rank = round(brand_sum / brand_count, 2)
        else:
            avg_brand_rank = 0
            
        brand_averages[brand] = avg_brand_rank
        overall_sum += brand_sum
        overall_count += brand_count
        
    if overall_count > 0:
        category_avg = round(overall_sum / overall_count, 2)
    else:
        category_avg = 0
        
    return {
        "product_averages": product_averages,
        "brand_averages": brand_averages,
        "category_average": {
            "overall_mobile_phones": category_avg
        }
    }


@handle_builder_exceptions
def keyword_matrix_builder(region_data: dict, task, products=None, template="template-name") -> tuple[bool, dict]:
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting KEYWORD_MATRIX JSON build | Task={t_id}")
    
    keyword_matrix = build_keyword_matrix(region_data, products)
    keyword_summary = build_rank_averages(keyword_matrix)
    
    payload = {
        "matrix": keyword_matrix,
        "summary": keyword_summary
    }
    
    logger.info(f"Completed KEYWORD_MATRIX JSON build | Task={t_id}")
    return False, payload
