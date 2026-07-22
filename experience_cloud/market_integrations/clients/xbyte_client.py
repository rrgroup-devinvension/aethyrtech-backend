import logging
from experience_cloud.api_provider.services import BaseApiClient
from experience_cloud.api_provider.exceptions import ApiProviderRequestError
from experience_cloud.api_provider.schemas import LogContextSchema

logger = logging.getLogger(__name__)

class XByteClient(BaseApiClient):
    """
    Unified XByte API Client using the centralized BaseApiClient.
    Inherits retries, dynamic configuration, and API key injection.
    """
    
    def __init__(self, provider_code="XBYTE"):
        # Initialize the base client with the specific provider code for XByte
        super().__init__(provider_code=provider_code)

    def fetch_results(self, keyword: str, location: str, platform: str, payload=None, log_context: LogContextSchema = None):
        """
        Fetch quick commerce product results from XByte API.
        Equivalent to the legacy QuickCommerceClient.fetch_results.
        """
        logger.info(f"QuickCommerce fetch → keyword={keyword}, pincode={location}, platform={platform}")
        
        # Determine specific payload structure per platform
        if payload is None:
            payload = {
                "endpoint": "result",
                "zipcode": location,
                "keyword": keyword,
                "platform": platform,
            }

        try:
            response = self.post(json=payload, log_context=log_context)
            if response.get("message") and not response.get("results"):
                raise ApiProviderRequestError(
                    message=response.get("message"),
                    extra=response
                )
                
            return response
            
        except ApiProviderRequestError as e:
            logger.warning(f"XByte API logical/request error → {e.message}")
            raise
        except Exception as e:
            logger.exception("XByte unexpected error")
            raise ApiProviderRequestError(
                message="XByte API failure",
                extra=str(e)
            )
