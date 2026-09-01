import argparse
import logging
import os
import sys

import django
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


def main():
    """Parse args and import xbytes reviews from files."""
    from experience_cloud.market_integrations.models.xbytes import XBytesReview

    parser = argparse.ArgumentParser(description='Import reviews into XBytes database.')
    parser.add_argument(
        '--dir', type=str, default='scripts/reviews', help='Directory containing review Excel/TSV/CSV files.'
    )
    parser.add_argument(
        '--platform', type=str, default=None, help='Only import files matching this platform (e.g., amazon_uae).'
    )

    args = parser.parse_args()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    directory = os.path.join(base_dir, args.dir.replace('\\', '/').strip('/'))

    if not os.path.exists(directory):
        logger.error(f"Directory not found: {directory}")
        return

    files = [f for f in os.listdir(directory) if f.endswith(('.xlsx', '.xls', '.csv', '.tsv'))]
    if not files:
        logger.info(f"No valid Excel/CSV/TSV files found in {directory}")
        return

    total_saved = 0

    for filename in files:
        # Extract platform from filename (e.g. Amazon_uae_reviews_full.xlsx -> amazon_uae)
        file_platform = filename.lower().split('_reviews')[0].strip()

        if args.platform and file_platform != args.platform.lower():
            continue

        filepath = os.path.join(directory, filename)
        logger.info(f"Processing {filename} (Platform: {file_platform})...")
        file_saved = 0

        try:
            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            else:
                delimiter = '\t' if filename.endswith('.tsv') else ','
                df = pd.read_csv(filepath, delimiter=delimiter)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to read {filename}: {e}")
            continue

        # Replace NaN with empty string
        df = df.fillna('')

        # Find URL column dynamically if needed
        url_col = None
        for col in df.columns:
            if str(col).lower().startswith('platform url'):
                url_col = col
                break

        reviews_to_create = []
        for _index, row in df.iterrows():
            product_url = (
                str(row.get(url_col, row.get('product_url', '')))
                if url_col or 'product_url' in df.columns else ''
            )

            sku = str(row.get('sku_id', '')).strip()

            review = XBytesReview(
                platform=file_platform,
                product_url=product_url,
                product_title=str(row.get('product_title', '')),
                sku=sku,
                brand=str(row.get('brand', '')),
                review_id=str(row.get('review_id', '')),
                reviewer_name=str(row.get('reviewer_name', '')),
                reviewer_profile_url=str(row.get('reviewer_profile_url', '')),
                rating=str(row.get('rating', '')),
                review_title=str(row.get('review_title', '')),
                review_text=str(row.get('review_text', '')),
                review_date=str(row.get('review_date', '')),
                verified_purchase=str(row.get('verified_purchase', '')),
                helpful_count=str(row.get('helpful_count', '')),
                review_images=str(row.get('review_images', '')),
                video_urls=str(row.get('video_urls', '')),
                variant_info=str(row.get('variant_info', '')),
                review_url=str(row.get('review_url', '')),
                timestamp=str(row.get('timestamp', ''))
            )
            reviews_to_create.append(review)

            if len(reviews_to_create) >= 1000:
                XBytesReview.objects.bulk_create(
                    reviews_to_create,
                    update_conflicts=True,
                    update_fields=[
                        'product_url', 'product_title', 'brand', 'reviewer_name',
                        'reviewer_profile_url', 'rating', 'review_title', 'review_text',
                        'review_date', 'verified_purchase', 'helpful_count', 'review_images',
                        'video_urls', 'variant_info', 'review_url', 'timestamp'
                    ]
                )
                file_saved += len(reviews_to_create)
                total_saved += len(reviews_to_create)
                reviews_to_create = []

        if reviews_to_create:
            XBytesReview.objects.bulk_create(
                reviews_to_create,
                update_conflicts=True,
                update_fields=[
                    'product_url', 'product_title', 'brand', 'reviewer_name',
                    'reviewer_profile_url', 'rating', 'review_title', 'review_text',
                    'review_date', 'verified_purchase', 'helpful_count', 'review_images',
                    'video_urls', 'variant_info', 'review_url', 'timestamp'
                ]
            )
            file_saved += len(reviews_to_create)
            total_saved += len(reviews_to_create)

        logger.info(f"Finished {filename}. Saved/Updated {file_saved} reviews from this file.")

    logger.info(f"\n✅ Import complete! Successfully processed and saved/updated {total_saved} total reviews.")

if __name__ == "__main__":
    main()
