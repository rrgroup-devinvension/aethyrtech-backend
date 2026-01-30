import logging
from datetime import datetime
from collections import defaultdict
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import match_brand, get_brand_pincodes

logger = logging.getLogger(__name__)

def get_unique_keywords(data):
    unique_keywords = set()
    for platform, keywords in data.items():
        for kw in keywords:
            if kw:
                unique_keywords.add(str(kw).strip())

    return list(unique_keywords)

def build_keyword_matrix(brands, keywords, products, brand_name, platform_type):
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    brand_keywords = get_unique_keywords(keywords)
    brand_pincodes = get_brand_pincodes().get(brand_name) or ["000000"]
    for p in products:
        if not p.brand or not p.title or not p.uid:
            continue
        product_brand = str(p.brand).strip()
        matched_brand = None
        for b in brands:
            if match_brand(product_brand, b):
                matched_brand = b
                break
        if not matched_brand:
            print(product_brand)
            continue
        brand = matched_brand 
        title = str(p.title).strip()
        ranking_data = p.rankings or {}
        product_pincode = brand_pincodes
        if p.platform_type == "marketplace":
            product_pincode = ["000000"]
        for pincode in product_pincode:
            if pincode not in result[brand][title]:
                result[brand][title][pincode] = { kw: 0 for kw in brand_keywords }
            rank_entries = ranking_data.get(pincode, [])
            keyword_rank_bucket = defaultdict(list)
            for entry in rank_entries:
                kw = entry.get("keyword")
                rank = entry.get("rank")
                if kw and rank:
                    keyword_rank_bucket[kw].append(rank)
            for kw, ranks in keyword_rank_bucket.items():
                avg_rank = round(sum(ranks) / len(ranks))
                if kw in result[brand][title][pincode]:
                    result[brand][title][pincode][kw] = avg_rank
    return result


def build_rank_averages(keyword_matrix):
    product_averages = {}
    brand_averages = {}
    all_brand_values = []
    for brand, products in keyword_matrix.items():
        brand_rank_values = []
        for product_title, pincodes in products.items():
            product_rank_values = []
            for pincode, keyword_ranks in pincodes.items():
                for kw, rank in keyword_ranks.items():
                    if rank and rank > 0:
                        product_rank_values.append(rank)
            if product_rank_values:
                avg_product_rank = round(sum(product_rank_values) / len(product_rank_values), 2)
            else:
                avg_product_rank = 0
            product_averages[product_title] = avg_product_rank
            if avg_product_rank > 0:
                brand_rank_values.append(avg_product_rank)
        if brand_rank_values:
            avg_brand_rank = round(sum(brand_rank_values) / len(brand_rank_values), 2)
        else:
            avg_brand_rank = 0
        brand_averages[brand] = avg_brand_rank
        if avg_brand_rank > 0:
            all_brand_values.append(avg_brand_rank)
    if all_brand_values:
        category_avg = round(sum(all_brand_values) / len(all_brand_values), 2)
    else:
        category_avg = 0
    return {
        "product_averages": product_averages,
        "brand_averages": brand_averages,
        "category_average": {
            "overall_mobile_phones": category_avg
        }
    }


def keyword_matrix_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template="catalog", platform_type=None):
    logger.info(f"Starting CATALOG JSON build | Task={task.id}")
    try:
        keyword_matrix = build_keyword_matrix(brands, keywords, products, brand_name, platform_type)
        keyword_summary = build_rank_averages(keyword_matrix)
        payload = {
            "matrix": keyword_matrix,
            "summary": keyword_summary
        }
        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except SchedulerBaseException:
        raise
    except Exception as exc:
        logger.exception("Catalog JSON build failed")
        raise DataProcessingException(
            message="Catalog JSON build failed",
            extra=str(exc)
        )
