import logging
import time

from experience_cloud.market_data.schemas import DataDumpResponseSchema, DataDumpSchema
from experience_cloud.market_data.services.base_service import BaseDataDumpService

logger = logging.getLogger(__name__)

class DummyDataDumpService(BaseDataDumpService):
    """A mock service to simulate a data dump without making real API calls."""

    def execute(self, schema: DataDumpSchema) -> DataDumpResponseSchema:
        """Simulate an API request and return a mock success response."""
        logger.info(f"[DUMMY] Executing Data Dump for: {schema.get('keyword_name')} @ {schema.get('display_location')}")

        # Simulate network latency
        time.sleep(5)

        logger.info(f"[DUMMY] Successfully scraped mock data for {schema.get('keyword_name')}")

        return {
            "status": "success",
            "items_count": 10,
            "message": "Dummy scrape successful!"
        }
