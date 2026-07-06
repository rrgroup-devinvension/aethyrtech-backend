import os
import sys
import json
from pathlib import Path
from typing import Set

# Setup Django environment
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.scheduler.models import QuickCommerceProduct
from django.db import transaction

def get_json_files(directory: str) -> list:
    """Recursively find all JSON files in the given directory."""
    path = Path(directory)
    return list(path.rglob("*.json"))

def is_valid_value(val) -> bool:
    """Check if the extracted value is valid (not empty, null, or NA)."""
    if val is None:
        return False
    if isinstance(val, str):
        val = val.strip()
        if not val or val.upper() == "NA":
            return False
    return True

def process_json_dumps(target_dir: str):
    json_files = get_json_files(target_dir)
    print(f"Found {len(json_files)} JSON files in {target_dir}")

    updated_ids: Set[str] = set()
    total_records_processed = 0
    total_records_updated = 0

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            results = data.get("results", [])
            if not results:
                continue
                
            # Process results inside the file
            for item in results:
                total_records_processed += 1
                prod_id = item.get("id")
                
                if not prod_id:
                    continue
                    
                if prod_id in updated_ids:
                    continue
                    
                detail = item.get("detail_data", {})
                brand_rating = detail.get("brand_rating")
                
                if is_valid_value(brand_rating):
                    brand_reviews = detail.get("brand_reviews", "")
                    brand_review_text = detail.get("brand_review_text", "")
                    print(prod_id, brand_rating, brand_reviews)
                    
                    # Update database (Updating all occurrences of this product UID)
                    with transaction.atomic():
                        QuickCommerceProduct.objects.filter(product_uid=prod_id).update(
                            brand_rating=brand_rating,
                            brand_reviews=brand_reviews,
                            brand_review_text=brand_review_text
                        )
                    
                    updated_ids.add(prod_id)
                    total_records_updated += 1
                    
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

    print("--- Update Summary ---")
    print(f"Total JSON files processed: {len(json_files)}")
    print(f"Total product records scanned: {total_records_processed}")
    print(f"Total unique products updated: {total_records_updated}")

if __name__ == "__main__":
    # Default target directory for quickcommerce JSON dumps
    default_target_dir = os.path.join(backend_dir, "media", "quickcommerce")
    
    # You can pass a different path as a command-line argument
    target_dir = sys.argv[1] if len(sys.argv) > 1 else default_target_dir
    
    print(f"Starting database update using JSON files from: {target_dir}")
    process_json_dumps(target_dir)
