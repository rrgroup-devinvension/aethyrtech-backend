import logging
from datetime import datetime
from collections import defaultdict
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import match_brand, get_brand_pincodes
from apps.scheduler.enums import JsonTemplate

logger = logging.getLogger(__name__)
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

import re

def count_occurrence(text, keyword):
    if not text or not keyword:
        return 0

    # convert to lowercase → ignore case
    text_words = set(re.findall(r'\w+', text.lower()))
    keyword_words = re.findall(r'\w+', keyword.lower())

    # return 1 if ANY keyword word exists in text
    return 1 if any(word in text_words for word in keyword_words) else 0

def build_keyword_count(keywords, products, brand_name):
    result = defaultdict(dict)
    brand_pincodes = get_brand_pincodes().get(brand_name) or ["000000"]
    for platform, keyword_list in keywords.items():
        platform_products = [
            p for p in products
            if p.platform == platform and match_brand(brand_name, p.brand)
        ]
        for p in platform_products:
            product_title = p.title
            result[platform][product_title] = []
            ranking_data = p.rankings or {}
            ranked_keywords = set()
            for pin, rank_list in ranking_data.items():
                for r in rank_list:
                    if r.get("platform") == platform:
                        kw = r.get("keyword")
                        if kw:
                            ranked_keywords.add(kw.strip().lower())
            for kw in keyword_list:
                if not kw:
                    continue

                kw_clean = kw.strip().lower()

                # Always count keyword presence
                title_count = count_occurrence(p.title, kw_clean)
                desc_count = count_occurrence(p.description, kw_clean)
                bullets_text = " ".join(p.bullets) if p.bullets else ""
                bullet_count = count_occurrence(bullets_text, kw_clean)

                result[platform][product_title].append({
                    "keyword": kw,
                    "is_ranked": kw_clean in ranked_keywords,
                    "counts": {
                        "title": title_count,
                        "description": desc_count,
                        "bullets": bullet_count
                    }
                })

    return result

def keyword_counts_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template=JsonTemplate.KEYWORD_COUNTS.slug, platform_type=None):
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting KEYWORD_COUNTS JSON build | Task={t_id}")
    try:
        log_start(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        payload = build_keyword_count(keywords, products, brand_name)
        result = save_json_to_file(task, payload, brand_id, brand_name, template)
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
