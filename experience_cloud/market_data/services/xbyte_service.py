import json
import logging
import os
from datetime import datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import get_valid_filename

from experience_cloud.api_provider.schemas import LogContextSchema
from experience_cloud.market_data.schemas import DataDumpResponseSchema, DataDumpSchema
from experience_cloud.market_data.services.base_service import BaseDataDumpService
from experience_cloud.market_integrations.clients.xbyte_client import XByteClient
from experience_cloud.market_integrations.models.xbytes import XBytesProduct

logger = logging.getLogger(__name__)

class XByteDataDumpService(BaseDataDumpService):
    """Service to handle XByte data dumps."""

    def execute(self, schema: DataDumpSchema) -> DataDumpResponseSchema:
        """Dynamically generates the payload from the Platform's JSON config.

        Executes the POST request using the centralized ApiClient,
        and atomic-upserts the results into the XBytesProduct table.
        """
        try:
            platform_config = schema.get("configuration", {})
            provider_code = schema.get("provider_code", "XBYTE")
            location = schema.get("display_location")
            keyword = schema.get("keyword_name")
            platform = schema.get("platform_name")
            payload= None

            # If there's no dynamic configuration provided from the DB, fallback to an error
            ctx = (
                f"[{provider_code} | {schema.get('brand_name') or 'NoBrand'} | "
                f"{schema.get('category_name') or 'NoCat'} | {schema.get('platform_name') or 'NoPlatform'} | "
                f"{schema.get('keyword_name') or 'NoKeyword'} | {schema.get('display_location') or 'NoLoc'}]"
            )

            # Build variable context for templating
            variables = {
                "keyword": keyword or "",
                "location": location or "",
                "platform": schema.get("platform_code") or "",
                "category": schema.get("category_name") or "",
                "brand": schema.get("brand_name") or ""
            }

            # Use the Circuit-Breaker ApiClient!
            client = XByteClient(provider_code=provider_code)

            if not platform_config:
                logger.warning(
                    f"{ctx} Using fallback config for {provider_code}. "
                    "Please update Platform configuration in Django Admin."
                )
                payload = {
                    "endpoint": "result",
                    "zipcode": location,
                    "keyword": keyword,
                    "platform": platform,
                }
            else:
                logger.info(f"{ctx} Generating dynamic payload from platform configuration using generic engine...")
                _, prepared_payload = client.prepare_body(platform_config, variables)
                logger.info(f"{ctx} Prepared Payload: {json.dumps(prepared_payload, indent=2)}")

            log_context: LogContextSchema = {
                "platform_id": schema.get("platform_id"),
                "category_id": schema.get("category_id"),
                "keyword_name": schema.get("keyword_name"),
                "location_name": schema.get("display_location"),
                "regions": schema.get("regions")
            }

            # Make the API call
            logger.info(
                f"{ctx} Making external API call to "
                f"location: {location}, "
                f"keyword: {keyword}, "
                f"platform: {platform}"
            )
            assert keyword is not None
            assert location is not None
            assert platform is not None

            response_data = client.fetch_results(
                keyword=keyword,
                location=location,
                platform=platform,
                payload=prepared_payload if platform_config else payload,
                log_context=log_context
            )

            # Save the raw response to the media folder
            logger.info(f"{ctx} API call successful. Saving raw JSON response to media folder...")
            if isinstance(response_data, dict):
                self._save_raw_json_to_media(schema, response_data)

            # Extract Results
            results = response_data.get("results", []) if isinstance(response_data, dict) else []

            items_count = len(results)
            logger.info(f"{ctx} Extracted {items_count} products from API response.")

            if items_count == 0:
                logger.info(f"{ctx} No results found. Skipping database insertion.")
                return DataDumpResponseSchema(status="success", items_count=0, message="No results found.")

            # Map and Upsert into Database
            logger.info(f"{ctx} Starting database upsert for {items_count} products...")
            self._save_to_database(schema, results)
            logger.info(f"{ctx} Successfully upserted {items_count} products into the database.")

            return DataDumpResponseSchema(
                status="success",
                items_count=items_count,
                message=f"Successfully extracted {items_count} items."
            )

        except Exception as e:
            from experience_cloud.api_provider.exceptions import ApiProviderRequestError
            logger.exception(f"XByte execution failed: {e}")
            
            error_msg = str(e)
            if isinstance(e, ApiProviderRequestError) and isinstance(e.extra, dict):
                error_msg = json.dumps(e.extra, indent=4)
                
                # Save the error response to media folder
                logger.info("Saving error JSON response to media folder...")
                self._save_raw_json_to_media(schema, e.extra)
                
            return DataDumpResponseSchema(status="error", items_count=0, message=error_msg)


    def _save_raw_json_to_media(self, schema: DataDumpSchema, response_data: dict):
        """Saves the complete JSON response to the Django media folder in a structured hierarchy.

        Path: MEDIA_ROOT/market_data_dumps/provider_code/date/category/platform/keyword/location/filename.json.
        """
        try:
            # Safely generate parts of the path
            date_str = datetime.now().strftime('%Y-%m-%d')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            provider_code = schema.get("provider_code")
            assert provider_code is not None
            category = get_valid_filename(schema.get("category_name") or "uncategorized")
            platform = get_valid_filename(schema.get("platform_code") or "unknown_platform")
            keyword = get_valid_filename(schema.get("keyword_name") or "unknown_keyword")
            location = get_valid_filename(schema.get("display_location") or "unknown_location")

            # Construct path
            base_dir = os.path.join(
                settings.MEDIA_ROOT,
                "market_data_dumps",
                provider_code,
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
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to save raw JSON to media folder: {e}")
            # We don't raise the error here so that the main execution can still save to the DB!

    def _save_to_database(self, schema: DataDumpSchema, results: list):
        run_date = timezone.now().strftime('%Y-%m-%d')
        platform_code = schema["platform_code"]
        keyword_name = schema["keyword_name"]
        location_str = schema["display_location"]

        with transaction.atomic():
            new_products = []
                
            for item in results:
                detail = item.get("detail_data", {})
                product_uid = str(item.get("id", "")).strip()

                new_products.append(
                    XBytesProduct(
                        platform=platform_code,
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

                        # Manufacturer & Logistics
                        manufacturer=detail.get("manufacturer"),
                        manufacturer_part=detail.get("manufacturer_part"),
                        upc_retailer_id=detail.get("upc_retailer_id"),
                        model=detail.get("model"),
                        sold_by=detail.get("sold_by"),
                        shipped_by=detail.get("shipped_by"),
                        description=detail.get("description"),
                        bullets=detail.get("bullets", []),
                        
                        # Media Counts & Booleans
                        image_count=detail.get("images", 0) or 0,
                        video_count=detail.get("videos", 0) or 0,
                        document_count=detail.get("documents", 0),
                        product_view_360=detail.get("product_view_360", False),

                        run_date=run_date
                    )
                )

            XBytesProduct.objects.bulk_create(
                new_products,
                batch_size=500,
                update_conflicts=True,
                update_fields=[
                    'rank', 'title', 'brand', 'category', 'availability', 'mrp',
                    'sell_price', 'rating', 'reviews', 'brand_rating', 'brand_reviews', 'brand_review_text',
                    'product_url', 'thumbnail', 'main_image', 'images', 
                    'manufacturer', 'manufacturer_part', 'upc_retailer_id',
                    'model', 'sold_by', 'shipped_by',
                    'description', 'bullets', 'image_count', 'video_count', 'document_count', 'product_view_360',
                    'run_date'
                ]
            )
