import argparse
import json
import logging
import os
import sys

import django

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Setup Django environment so we can use its database connection
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


def main():
    """Parse args and count total catalog items for a region."""
    from django.conf import settings

    from experience_cloud.json_generator.models import RegionJsonFile, TemplateCodes

    parser = argparse.ArgumentParser(description='Calculate total number of items in a catalog JSON file.')
    parser.add_argument('region_id', type=int, help='The ID of the region.')

    args = parser.parse_args()
    region_id = args.region_id

    logger.info(f"Looking for catalog file for Region ID: {region_id}")

    try:
        region_file = RegionJsonFile.objects.get(
            region_id=region_id,
            template__template=TemplateCodes.CATALOG.value
        )
    except RegionJsonFile.DoesNotExist:
        logger.error(f"No catalog RegionJsonFile found for region_id {region_id}.")
        return
    except RegionJsonFile.MultipleObjectsReturned:
        logger.warning(f"Multiple catalog RegionJsonFiles found for region_id {region_id}. Using the first one.")
        region_file = RegionJsonFile.objects.filter(
            region_id=region_id,
            template__template=TemplateCodes.CATALOG.value
        ).first()

    file_path = region_file.file_path
    if not file_path:
        logger.error("The RegionJsonFile record does not have a file_path set.")
        return

    # Check if the path is absolute or relative
    abs_path = os.path.join(settings.BASE_DIR, file_path) if not os.path.isabs(file_path) else file_path

    if not os.path.exists(abs_path):
        # Try treating the path as relative to MEDIA_ROOT instead
        # Sometimes paths in db are like "brands/sleepwell/..." or "media/brands/..."
        # If the file_path already starts with 'media', we just use BASE_DIR which we did above.
        # If not, let's try MEDIA_ROOT.
        abs_path_media = os.path.join(settings.MEDIA_ROOT, file_path)
        if os.path.exists(abs_path_media):
            abs_path = abs_path_media
        elif os.path.exists(os.path.join(settings.BASE_DIR, "media", file_path)):
            abs_path = os.path.join(settings.BASE_DIR, "media", file_path)
        else:
            tried_paths = (
                f"- {abs_path}\n"
                f"- {abs_path_media}\n"
                f"- {os.path.join(settings.BASE_DIR, 'media', file_path)}"
            )
            logger.error(f"File not found. Tried paths:\n{tried_paths}")
            return

    logger.info(f"Found catalog JSON at: {abs_path}")

    try:
        with open(abs_path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to read or parse JSON file: {e}")
        return

    if not isinstance(data, dict):
        logger.error("Unexpected JSON structure: expected a dictionary mapping brands to lists of products.")
        return

    total_products = 0
    datasource_counts = {}
    datasource_unique = {}

    for brand, products in data.items():
        if isinstance(products, list):
            count = len(products)
            total_products += count

            brand_ds_counts = {}
            for product in products:
                if isinstance(product, dict):
                    ds = product.get("data_source") or "Unknown"
                    datasource_counts[ds] = datasource_counts.get(ds, 0) + 1
                    brand_ds_counts[ds] = brand_ds_counts.get(ds, 0) + 1

                    # Track unique SKUs (or IDs) per datasource
                    uid = product.get("sku") or product.get("id")
                    if uid:
                        if ds not in datasource_unique:
                            datasource_unique[ds] = set()
                        datasource_unique[ds].add(uid)

            ds_str = ", ".join([f"{ds}: {cnt}" for ds, cnt in brand_ds_counts.items()])
            if ds_str:
                logger.info(f"Brand '{brand}': {count} products ( {ds_str} )")
            else:
                logger.info(f"Brand '{brand}': {count} products")
        else:
            logger.warning(f"Brand '{brand}' does not contain a list of products. Skipping.")

    logger.info("-" * 40)
    logger.info("Counts by Datasource (Total vs Unique):")
    for ds, count in sorted(datasource_counts.items(), key=lambda x: x[1], reverse=True):
        unique_count = len(datasource_unique.get(ds, set()))
        logger.info(f"  {ds}: {count} total | {unique_count} unique")

    logger.info("-" * 40)
    logger.info(f"Total number of products across all brands: {total_products}")

if __name__ == "__main__":
    main()
