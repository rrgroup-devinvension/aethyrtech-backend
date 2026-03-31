import logging
from datetime import datetime
from collections import defaultdict
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import match_brand, get_brand_pincodes
from scripts.csv_logger import CSVLogger

logger = logging.getLogger(__name__)
csv_logger = CSVLogger("product_debug.csv")
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

def get_unique_keywords(data):
    unique_keywords = set()
    for platform, keywords in data.items():
        for kw in keywords:
            if kw:
                unique_keywords.add(str(kw).strip())

    return list(unique_keywords)

def build_keyword_matrix(brands, keywords, products, brand_name, platform_type):
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    aggregate_bucket = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )
    brand_keywords = get_unique_keywords(keywords)
    brand_pincodes = get_brand_pincodes().get(brand_name) or ["000000"]
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
                platform = entry.get("platform")
                csv_logger.append({
                    "product_id": p.uid,
                    "brand": brand,
                    "product": title,
                    "pincode": pincode,
                    "keyword": kw,
                    "platform": platform,
                    "ranking": rank
                })
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
    return result

def build_rank_averages(keyword_matrix):
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


def keyword_matrix_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template="keyword-matrix", platform_type=None):
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting KEYWORD_MATRIX JSON build | Task={t_id}")
    try:
        log_start(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        keyword_matrix = build_keyword_matrix(brands, keywords, products, brand_name, platform_type)
        keyword_summary = build_rank_averages(keyword_matrix)
        payload = {
            "matrix": keyword_matrix,
            "summary": keyword_summary
        }
        result = save_json_to_file(payload, brand_name, template)
        log_success(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        return result
    except SchedulerBaseException:
        raise
    except Exception as exc:
        logger.exception("Catalog JSON build failed")
        log_error(task_id=t_id, error=str(exc), extra={'template': template, 'brand_id': brand_id})
        raise DataProcessingException(
            message="Catalog JSON build failed",
            extra=str(exc)
        )
