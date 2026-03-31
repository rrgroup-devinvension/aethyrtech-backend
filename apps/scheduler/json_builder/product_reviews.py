import logging
from datetime import datetime
from collections import defaultdict
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import match_brands
from apps.scheduler.enums import JsonTemplate

logger = logging.getLogger(__name__)
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

import re

from collections import defaultdict
from datetime import datetime

def build_review_structure(products, brands=None):
    """
    Builds review JSON structure for ALL brands:

    {
        brand_name: {
            product_sku: [
                { review_data }
            ]
        }
    }

    If brand_name is provided → filters that brand only.
    """

    result = defaultdict(lambda: defaultdict(list))

    for p in products:
        product_brand = getattr(p, "brand", None)
        sku = getattr(p, "uid", None)

        if not product_brand or not sku:
            continue

        # If specific brand requested, filter
        matched_brand = match_brands(brands, product_brand)
        if product_brand and not matched_brand:
            continue

        reviews = getattr(p, "reviews", []) or []

        for review in reviews:
            try:
                review_data = {
                    "review_id": review.get("review_id"),
                    "rating": review.get("rating"),
                    "title": review.get("review_title"),
                    "review_text": review.get("review_text"),
                    "reviewer": review.get("reviewer_name"),
                    "verified": review.get("verified", False),
                    "review_date": review.get("review_date"),
                    "verified_purchase": review.get("verified_purchase"),
                    "platform": review.get("platform"),
                }
                result[matched_brand][sku].append(review_data)

            except Exception:
                logger.exception(
                    f"Failed processing review | Brand={product_brand} | SKU={sku}"
                )
                continue

    return result

def product_reviews_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template=JsonTemplate.PRODUCT_REVIEWS.slug, platform_type=None):
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting PRODUCT_REVIEWS JSON build | Task={t_id}")
    try:
        log_start(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        payload = build_review_structure(products, brands)
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
