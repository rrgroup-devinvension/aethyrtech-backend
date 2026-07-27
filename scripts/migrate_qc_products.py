import os
import sys

# Setup Django environment so we can use its database connection
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection
import json

def migrate_qc_products():
    print("Starting data migration from aethyrtech to xbytesdata...")

    # We use a single SQL INSERT ... SELECT query since both databases are on the same MySQL server.
    # This is dramatically faster and safer than fetching to python and inserting row-by-row.
    
    # We will use batched insert to avoid locking the tables for too long or blowing up the undo logs
    
    with connection.cursor() as cursor:
        # First, count total records to process
        cursor.execute("SELECT COUNT(*) FROM aethyrtech.qc_products")
        total_rows = cursor.fetchone()[0]
        
        if total_rows == 0:
            print("No records found in aethyrtech.qc_products.")
            return
            
        print(f"Total products to migrate: {total_rows}")
        
        batch_size = 5000
        offset = 0
        
        while offset < total_rows:
            # We use an INSERT IGNORE or standard INSERT. We'll use standard INSERT.
            # Using JSON_VALID to prevent MySQL errors when converting longtext to JSON column
            sql = f"""
            INSERT INTO xbytesdata.products (
                platform, keyword, location, product_uid, `rank`, title, brand, category,
                description, availability, mrp, sell_price, rating, reviews,
                brand_rating, brand_reviews, brand_review_text,
                manufacturer_part, model, upc_retailer_id,
                sold_by, shipped_by, product_url, thumbnail, main_image, images,
                image_count, video_count, document_count, product_view_360,
                bullets, run_date, created_at, updated_at
            )
            SELECT 
                p.platform, p.keyword, p.pincode, p.product_uid, p.`rank`, p.title, p.brand, p.category,
                d.description, p.availability, p.msrp, p.sell_price, p.rating, p.reviews,
                p.brand_rating, p.brand_reviews, p.brand_review_text,
                d.manufacturer_part, d.model, d.upc_retailer_id,
                d.sold_by, d.shipped_by, p.product_url, p.thumbnail, p.main_image, 
                IF(JSON_VALID(p.detail_page_images), p.detail_page_images, NULL),
                d.image_count, d.video_count, d.document_count, d.product_view_360,
                IF(JSON_VALID(d.bullets), d.bullets, NULL), d.run_date, p.created_at, NOW()
            FROM (
                SELECT * FROM aethyrtech.qc_products 
                ORDER BY id 
                LIMIT {batch_size} OFFSET {offset}
            ) p
            LEFT JOIN aethyrtech.qc_product_detail d ON p.id = d.product_id;
            """
            
            cursor.execute(sql)
            
            offset += batch_size
            print(f"  - Progress: {min(offset, total_rows)} / {total_rows} rows migrated")
            
    print("\nSuccess! Migration completed.")

if __name__ == "__main__":
    try:
        migrate_qc_products()
    except KeyboardInterrupt:
        print("\nMigration cancelled by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
