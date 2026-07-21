from experience_cloud.json_generator.decorators import handle_builder_exceptions
from typing import Dict, List, Optional, Any, Union
from experience_cloud.executions.models import JsonFileTask
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator
import logging
from collections import defaultdict
from experience_cloud.json_generator.utils import match_brands

logger = logging.getLogger(__name__)

def build_review_structure(products: ItemGenerator, brands: Optional[List[str]] = None) -> dict:
    """
    Builds review JSON structure for ALL brands:

    {
        brand_name: {
            product_sku: [
                { review_data }
            ]
        }
    }

    If brands is provided -> filters that brand only.
    """
    if brands is None:
        brands = []

    # Using standard dict for the final payload is safer for JSON serialization
    result = defaultdict(lambda: defaultdict(list))

    for p in products:
        product_brand = getattr(p, "brand", None)
        sku = getattr(p, "uid", None)

        if not product_brand or not sku:
            continue

        # If specific brands requested, filter
        matched_brand = match_brands(brands, product_brand)
        if not matched_brand:
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

    # Convert nested defaultdicts back to standard dicts
    final_dict = {}
    for brand, skus in result.items():
        final_dict[brand] = dict(skus)
        
    return final_dict

@handle_builder_exceptions
def product_reviews_builder(region_data: dict, task, products=None, template="template-name") -> tuple[bool, dict]:
    brands = region_data.get("brands", [])
    t_id = getattr(task, 'id', 'unknown')
    
    logger.info(f"Starting PRODUCT_REVIEWS JSON build | Task={t_id}")
    payload = build_review_structure(products, brands)
    
    logger.info(f"Completed PRODUCT_REVIEWS JSON build | Task={t_id}")
    return False, payload
