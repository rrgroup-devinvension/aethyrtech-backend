import logging
from datetime import datetime
from collections import defaultdict
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import match_brand, get_brand_pincodes

logger = logging.getLogger(__name__)

def count_occurrence(text, keyword):
    if not text or not keyword:
        return 0
    return text.lower().count(keyword.lower())

def build_keyword_count(keywords, products, brand_name):
    result = defaultdict(dict)
    brand_pincodes = get_brand_pincodes().get(brand_name) or ["000000"]
    for platform, keyword_list in keywords.items():
        platform_products = [
            p for p in products
            if p.platform == platform and match_brand(p.brand, brand_name)
        ]
        for p in platform_products:
            product_title = p.title
            result[platform][product_title] = []
            ranking_data = p.rankings or {}
            ranked_keywords = set()
            for pin, rank_list in ranking_data.items():
                for r in rank_list:
                    if r.get("platform") == platform:
                        ranked_keywords.add(r.get("keyword"))
            for kw in keyword_list:
                kw = kw.strip()
                if kw not in ranked_keywords:
                    result[platform][product_title].append({
                        "keyword": kw,
                        "counts": {
                            "title": 0,
                            "description": 0,
                            "bullets": 0
                        }
                    })
                    continue
                title_count = count_occurrence(p.title, kw)
                desc_count = count_occurrence(p.description, kw)
                bullets_text = " ".join(p.bullets) if p.bullets else ""
                bullet_count = count_occurrence(bullets_text, kw)
                result[platform][product_title].append({
                    "keyword": kw,
                    "counts": {
                        "title": title_count,
                        "description": desc_count,
                        "bullets": bullet_count
                    }
                })

    return result

def keyword_counts_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template="catalog", platform_type=None):
    logger.info(f"Starting CATALOG JSON build | Task={task.id}")
    try:
        payload = build_keyword_count(keywords, products, brand_name)
        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except SchedulerBaseException:
        raise
    except Exception as exc:
        logger.exception("Catalog JSON build failed")
        raise DataProcessingException(
            message="Catalog JSON build failed",
            extra=str(exc)
        )
