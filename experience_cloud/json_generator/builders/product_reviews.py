import logging

from experience_cloud.json_generator.decorators import handle_builder_exceptions
from experience_cloud.json_generator.schemas import BrandReviewsMatrix, RegionDataSchema, ReviewData
from experience_cloud.json_generator.utils import ItemGenerator

logger = logging.getLogger(__name__)

def build_review_structure(products: ItemGenerator | None) -> BrandReviewsMatrix:
    """Compile and normalize multi-platform product review data into a structured schema.

    Groups verified reviews, ratings, and feedback text hierarchically by brand and SKU.
    Applies optional brand filtering to isolate specific competitor segments.
    """
    # Using standard dict for the final payload is safer for JSON serialization
    result: BrandReviewsMatrix = {}

    visited_uids = set()
    for p in (products or []):
        sku = p.uid

        p_platform = getattr(p, "platform", None)
        # if p_platform == 'amazon_uae':
        uid_key = (p_platform, sku)
        if uid_key in visited_uids:
            continue
        visited_uids.add(uid_key)

        reviews = getattr(p, "reviews", []) or []

        for review in reviews:
            try:
                review_data = ReviewData(
                    review_id=review.get("review_id"),
                    rating=review.get("rating"),
                    title=review.get("review_title"),
                    review_text=review.get("review_text"),
                    reviewer=review.get("reviewer_name"),
                    verified=review.get("verified", False),
                    review_date=review.get("review_date"),
                    verified_purchase=review.get("verified_purchase"),
                    platform=review.get("platform"),
                )
                result.setdefault(p.brand, {}).setdefault(sku, []).append(review_data)

            except (KeyError, TypeError, AttributeError, ValueError):
                logger.exception(
                    f"Failed processing review | Brand={p.brand} | SKU={sku}"
                )
                continue

    return result

@handle_builder_exceptions
def product_reviews_builder(
    region_data: RegionDataSchema, task, products=None, template="template-name"
) -> tuple[bool, dict]:
    """Process unformatted product reviews into a structured JSON payload for the frontend dashboard."""
    t_id = getattr(task, 'id', 'unknown')

    logger.info(f"Starting PRODUCT_REVIEWS JSON build | Task={t_id}")
    payload = build_review_structure(products)

    logger.info(f"Completed PRODUCT_REVIEWS JSON build | Task={t_id}")
    return False, payload
