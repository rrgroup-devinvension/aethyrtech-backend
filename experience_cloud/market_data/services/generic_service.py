import logging

from experience_cloud.api_provider.schemas import LogContextSchema
from experience_cloud.api_provider.services import BaseApiClient
from experience_cloud.market_data.schemas import DataDumpResponseSchema, DataDumpSchema
from experience_cloud.market_data.services.base_service import BaseDataDumpService

logger = logging.getLogger(__name__)

class GenericDataDumpService(BaseDataDumpService):
    """A generic service that dynamically drives API requests using the Platform's JSON configuration."""

    def execute(self, schema: DataDumpSchema) -> DataDumpResponseSchema:
        """Execute the dynamic request based on the schema."""
        provider_code = schema.get("provider_code", "")
        platform_config = schema.get("configuration", {})

        ctx = (
            f"[{provider_code} | {schema.get('brand_name') or 'NoBrand'} | "
            f"{schema.get('category_name') or 'NoCat'} | {schema.get('platform_name') or 'NoPlatform'} | "
            f"{schema.get('keyword_name') or 'NoKeyword'} | {schema.get('display_location') or 'NoLoc'}]"
        )

        if not platform_config:
            error_msg = f"{ctx} No dynamic configuration provided in Platform. Cannot execute."
            logger.error(error_msg)
            return {
                "status": "error",
                "items_count": 0,
                "message": error_msg
            }

        try:
            from jsonpath_ng import parse

            # Build variable context for templating
            variables = {
                "keyword": schema.get("keyword_name") or "",
                "location": schema.get("display_location") or "",
                "platform": schema.get("platform_code") or "",
                "category": schema.get("category_name") or "",
                "brand": schema.get("brand_name") or ""
            }

            log_context: LogContextSchema = {
                "platform_id": schema.get("platform_id"),
                "category_id": schema.get("category_id"),
                "keyword_name": schema.get("keyword_name"),
                "location_name": schema.get("display_location"),
                "regions": schema.get("regions")
            }

            logger.info(f"{ctx} Initializing BaseApiClient for generic extraction...")
            client = BaseApiClient(provider_code=provider_code)

            logger.info(f"{ctx} Preparing dynamic request payload...")
            prepared_request = client.prepare_dynamic_request(platform_config, variables)

            logger.info(f"{ctx} Executing prepared request...")
            response_data = client.request(**prepared_request, log_context=log_context)

            items_count = 0

            # Only parse if response_data is a dict (json) or list
            if isinstance(response_data, (dict, list)):

                response_mapping = platform_config.get("response_mapping", {})
                data_path = response_mapping.get("data_path", "")

                if data_path:
                    try:
                        jsonpath_expr = parse(data_path)
                        matches = [match.value for match in jsonpath_expr.find(response_data)]

                        # If data_path points to an array, count the array items.
                        # If it points to multiple individual nodes, len(matches) works.
                        if len(matches) == 1 and isinstance(matches[0], list):
                            items_count = len(matches[0])
                        else:
                            items_count = len(matches)
                    except Exception as e:  # noqa: BLE001
                        logger.error(f"{ctx} Failed to parse JSONPath '{data_path}': {e}")
            else:
                logger.warning(f"{ctx} Response was not JSON, skipping JSONPath extraction.")

            logger.info(f"{ctx} Extraction successful. Found {items_count} items.")

            return {
                "status": "success",
                "items_count": items_count,
                "message": f"Dynamic extraction successful. Found {items_count} items."
            }

        except Exception as e:
            logger.exception(f"{ctx} Critical failure during generic execution: {e!s}")
            return {
                "status": "error",
                "items_count": 0,
                "message": str(e)
            }
