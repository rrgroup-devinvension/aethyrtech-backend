import argparse
import json
import logging
import os
import sys

import django

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


def main():
    """Parse args and check SKUs in catalog."""
    from django.conf import settings

    from experience_cloud.json_generator.models import RegionJsonFile, TemplateCodes

    parser = argparse.ArgumentParser(description='Check SKUs in catalog against target lists.')
    parser.add_argument('region_id', type=int, help='The ID of the region.')
    parser.add_argument('platform', type=str, help='The platform/datasource to check (e.g. amazon_uae).')

    args = parser.parse_args()
    region_id = args.region_id
    platform = args.platform

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
        region_file = RegionJsonFile.objects.filter(
            region_id=region_id,
            template__template=TemplateCodes.CATALOG.value
        ).first()

    file_path = region_file.file_path
    if not file_path:
        return

    abs_path = os.path.join(settings.BASE_DIR, file_path) if not os.path.isabs(file_path) else file_path
    if not os.path.exists(abs_path):
        abs_path_media = os.path.join(settings.MEDIA_ROOT, file_path)
        if os.path.exists(abs_path_media):
            abs_path = abs_path_media
        elif os.path.exists(os.path.join(settings.BASE_DIR, "media", file_path)):
            abs_path = os.path.join(settings.BASE_DIR, "media", file_path)

    try:
        with open(abs_path, encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to read JSON: {e}")
        return

    # Extract SKUs for the given platform from the JSON
    json_skus = set()
    for _brand, products in data.items():
        if isinstance(products, list):
            for product in products:
                if isinstance(product, dict) and product.get("data_source") == platform:
                    uid = product.get("sku") or product.get("id")
                    if uid:
                        json_skus.add(str(uid).strip())

    list_path = os.path.join(os.path.dirname(__file__), "sku_lists", f"{platform}.txt")
    if not os.path.exists(list_path):
        logger.error(f"Target list file not found: {list_path}")
        return

    with open(list_path, encoding='utf-8') as f:
        target_skus = {line.strip() for line in f if line.strip()}

    matches = target_skus.intersection(json_skus)
    missing = target_skus - json_skus
    extra = json_skus - target_skus

    # Print summary to console
    logger.info(f"--- SKU Check for {platform} ---")
    logger.info(f"Target SKUs provided: {len(target_skus)}")
    logger.info(f"SKUs found in Catalog JSON: {len(json_skus)}")
    logger.info(f"MATCHED: {len(matches)}")
    logger.info(f"MISSING (in list but not in JSON): {len(missing)}")
    logger.info(f"EXTRA (in JSON but not in list): {len(extra)}")

    # Write detailed output to a report file
    report_path = os.path.join(os.path.dirname(__file__), "sku_lists", f"{platform}_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"--- SKU Check Report for {platform} ---\n")
        f.write(f"Target SKUs provided: {len(target_skus)}\n")
        f.write(f"SKUs found in Catalog JSON: {len(json_skus)}\n")
        f.write(f"MATCHED: {len(matches)}\n")
        f.write(f"MISSING: {len(missing)}\n")
        f.write(f"EXTRA: {len(extra)}\n\n")

        if matches:
            f.write("MATCHED SKUS:\n")
            f.write(", ".join(sorted(matches)) + "\n\n")

        if missing:
            f.write("MISSING SKUS:\n")
            f.write(", ".join(sorted(missing)) + "\n\n")

        if extra:
            f.write("EXTRA SKUS:\n")
            f.write(", ".join(sorted(extra)) + "\n\n")

    logger.info(f"\nDetailed report successfully saved to: {report_path}")

if __name__ == "__main__":
    main()
