import logging
from django.db import transaction
from experience_cloud.market_integrations.models.xbytes import XBytesProduct

logger = logging.getLogger(__name__)

def clean_stale_batch_products(batch_id: str):
    """
    Cleans up missing products for all platform/keyword/location combinations
    that were part of the given batch, but were NOT included in the batch.
    
    This ensures that if a product drops out of stock and is missing from the 
    batch of Excel files, it gets deleted from the database.
    """
    if not batch_id:
        logger.warning("clean_stale_batch_products called without a batch_id.")
        return

    # 1. Find all distinct (platform, keyword, location) combinations that WERE updated in this batch
    batch_combinations = XBytesProduct.objects.filter(
        last_seen_batch_id=batch_id
    ).values_list('platform', 'keyword', 'location').distinct()

    if not batch_combinations.exists():
        logger.warning(f"No products found with batch_id={batch_id}. Skipping cleanup.")
        return

    total_deleted = 0
    with transaction.atomic():
        # 2. For each combination, delete products that DO NOT have this batch_id
        for platform_code, keyword_name, location_str in batch_combinations:
            deleted_count, _ = XBytesProduct.objects.filter(
                platform=platform_code,
                keyword=keyword_name,
                location=location_str
            ).exclude(
                last_seen_batch_id=batch_id
            ).delete()
            
            if deleted_count > 0:
                logger.info(
                    f"[Batch {batch_id}] Cleaned up {deleted_count} stale products "
                    f"for {platform_code} -> {keyword_name} -> {location_str}"
                )
                total_deleted += deleted_count

    logger.info(f"Batch {batch_id} cleanup complete. Total stale products deleted: {total_deleted}")
