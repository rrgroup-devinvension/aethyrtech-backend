from experience_cloud.market_integrations.clients.xbyte_client import XByteClient
import os
import json
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.utils.text import get_valid_filename
import logging

from experience_cloud.market_data.services.base_service import BaseDataDumpService
from experience_cloud.market_data.schemas import DataDumpSchema, DataDumpResponseSchema

from experience_cloud.api_provider.services import BaseApiClient
from experience_cloud.market_integrations.models.xbytes import XBytesProduct
from experience_cloud.api_provider.schemas import LogContextSchema

logger = logging.getLogger(__name__)

class XByteDataDumpService(BaseDataDumpService):
    
    def execute(self, schema: DataDumpSchema) -> DataDumpResponseSchema:
        """
        Dynamically generates the payload from the Platform's JSON config,
        executes the POST request using the centralized ApiClient,
        and atomic-upserts the results into the XBytesProduct table.
        """
        try:
            platform_config = schema.get("configuration", {})
            provider_code = schema.get("provider_code", "XBYTE")
            location=schema.get("display_location"), 
            keyword=schema.get("keyword_name"), 
            platform=schema.get("platform_name")
            payload= None
            
            # If there's no dynamic configuration provided from the DB, fallback to an error
            if not platform_config:
                # Fallback for now to prevent immediate crashes during testing if DB isn't updated yet
                payload = {
                    "endpoint": "result",
                    "zipcode": location,
                    "keyword": keyword,
                    "platform": platform,
                }
                logger.warning(f"Using fallback config for {provider_code}. Please update Platform configuration in Django Admin.")
            else:
                # This is the MAGIC that replaces your placeholders!
                # 1. Convert the JSON configuration into a raw string
                payload_str = json.dumps(platform_config)
                
                # 2. Replace the exact placeholder texts with the actual variables
                payload_str = payload_str.replace("{keyword}", schema.get("keyword_name") or "")
                payload_str = payload_str.replace("{location}", schema.get("display_location") or "")
                payload_str = payload_str.replace("{platform}", schema.get("platform_code") or "")
                payload_str = payload_str.replace("{category}", schema.get("category_name") or "")
                
                # 3. Convert the string back into a Python Dictionary!
                payload = json.loads(payload_str)
            
            endpoint = payload.get("endpoint", "")
            
            log_context: LogContextSchema = {
                "brand_id": schema.get("brand_id"),
                "brand_name": schema.get("brand_name"),
                "platform_id": schema.get("platform_id"),
                "category_id": schema.get("category_id"),
                "keyword_id": schema.get("keyword_id"),
                "location_id": schema.get("location_id")
            }
            
            # Use the Circuit-Breaker ApiClient!
            client = XByteClient()
            
            # Make the API call
            logger.info(f"Posting dynamic payload to {provider_code} at {endpoint}")
            response_data = client.fetch_results(keyword=keyword, location=location, platform=platform, payload=payload, log_context=log_context)
            
            # Save the raw response to the media folder
            self._save_raw_json_to_media(schema, response_data)
            
            # Extract Results
            if isinstance(response_data, dict):
                results = response_data.get("results", [])
            else:
                results = []
                
            items_count = len(results)
            
            if items_count == 0:
                return DataDumpResponseSchema(status="success", items_count=0, message="No results found.")

            # Map and Upsert into Database
            self._save_to_database(schema, results)
            
            return DataDumpResponseSchema(
                status="success", 
                items_count=items_count, 
                message=f"Successfully extracted {items_count} items."
            )
            
        except Exception as e:
            logger.exception(f"XByte execution failed: {e}")
            return DataDumpResponseSchema(status="error", items_count=0, message=str(e))

    def _save_raw_json_to_media(self, schema: DataDumpSchema, response_data: dict):
        """
        Saves the complete JSON response to the Django media folder in a structured hierarchy.
        Path: MEDIA_ROOT/market_data_dumps/date/category/platform/keyword/location/filename.json
        """
        try:
            # Safely generate parts of the path
            date_str = datetime.now().strftime('%Y-%m-%d')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            category = get_valid_filename(schema.get("category_name") or "uncategorized")
            platform = get_valid_filename(schema.get("platform_name") or "unknown_platform")
            keyword = get_valid_filename(schema.get("keyword_name") or "unknown_keyword")
            location = get_valid_filename(schema.get("display_location") or "unknown_location")
            
            # Construct path
            base_dir = os.path.join(
                settings.MEDIA_ROOT, 
                "market_data_dumps", 
                date_str, 
                category, 
                platform, 
                keyword, 
                location
            )
            
            # Create directories if they don't exist
            os.makedirs(base_dir, exist_ok=True)
            
            # File name
            filename = f"{platform}_{keyword}_{location}_{timestamp}.json"
            filepath = os.path.join(base_dir, filename)
            
            # Save file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=4)
                
            logger.info(f"Saved raw XByte JSON response to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save raw JSON to media folder: {e}")
            # We don't raise the error here so that the main execution can still save to the DB!

    
    def _save_to_database(self, schema: DataDumpSchema, results: list):
        run_date = timezone.now().strftime('%Y-%m-%d')
        platform_name = schema["platform_name"]
        keyword_name = schema["keyword_name"]
        location_str = schema["display_location"]
        
        with transaction.atomic():
            new_products = []
            for item in results:
                detail = item.get("detail_data", {})
                product_uid = str(item.get("id", "")).strip()
                
                new_products.append(
                    XBytesProduct(
                        platform=platform_name,
                        keyword=keyword_name,
                        location=location_str,
                        product_uid=product_uid,
                        rank=item.get("rank"),
                        title=item.get("product_title"),
                        brand=item.get("brand"),
                        category=item.get("category"),
                        availability=item.get("availability"),
                        mrp=item.get("msrp"),
                        sell_price=detail.get("sell_price"),
                        rating=detail.get("rating"),
                        reviews=detail.get("reviews"),
                        brand_rating=detail.get("brand_rating"),
                        brand_reviews=detail.get("brand_reviews"),
                        brand_review_text=detail.get("brand_review_text"),
                        product_url=item.get("Platform url of the SKU"),
                        thumbnail=item.get("thumbnail_image_url"),
                        main_image=item.get("main_image"),
                        images=item.get("detail_page_images"),
                        
                        # Detail fields
                        model=detail.get("model"),
                        sold_by=detail.get("sold_by"),
                        shipped_by=detail.get("shipped_by"),
                        description=detail.get("description"),
                        bullets=detail.get("bullets", []),
                        image_count=detail.get("images", 0) or 0,
                        video_count=detail.get("videos", 0) or 0,
                        
                        # Store raw JSON
                        raw_data=item,
                        run_date=run_date
                    )
                )
                
            XBytesProduct.objects.bulk_create(
                new_products, 
                batch_size=500,
                update_conflicts=True,
                unique_fields=['platform', 'keyword', 'location', 'product_uid'],
                update_fields=[
                    'rank', 'title', 'brand', 'category', 'availability', 'mrp', 
                    'sell_price', 'rating', 'reviews', 'product_url', 'thumbnail', 
                    'main_image', 'images', 'model', 'sold_by', 'shipped_by', 
                    'description', 'bullets', 'image_count', 'video_count', 
                    'raw_data', 'run_date'
                ]
            )