import logging

from experience_cloud.api_provider.models import ApiProviderCodes
from experience_cloud.market_data.schemas import DataDumpResponseSchema, DataDumpSchema
from experience_cloud.market_data.services.xbyte_service import XByteDataDumpService

# Import your provider services here as you build them

logger = logging.getLogger(__name__)

class DataDumpDispatcher:
    """Routes the Data Dump Schema to the exact Service class based on the provider_code."""

    def __init__(self):
        """Initialize the dispatcher and its service registry."""
        # The Registry Map: Links a provider_code from the DB to the Python class that handles it.
        self._services = {
            ApiProviderCodes.XBYTES.value.upper(): XByteDataDumpService(),
        }

    def execute(self, schema: DataDumpSchema) -> DataDumpResponseSchema:
        """Execute the appropriate service based on the schema's provider code."""
        # Extract the provider_code we dynamically fetched from the DB
        provider_code = schema.get("provider_code", "").upper()

        # Look up the specific service instance
        service = self._services.get(provider_code)

        if not service:
            error_msg = f"No Data Dump Service registered for provider_code: '{provider_code}'"
            logger.error(error_msg)
            return DataDumpResponseSchema(
                status="error",
                items_count=0,
                message=error_msg
            )

        try:
            # Route the payload to the matching service
            logger.info(f"Dispatching Data Dump Job for {schema.get('keyword_name')} to {provider_code}")
            return service.execute(schema)

        except Exception as e:
            logger.exception(f"Critical failure inside {provider_code} Data Dump Service: {e!s}")
            return DataDumpResponseSchema(
                status="error",
                items_count=0,
                message=str(e)
            )
