import logging
from typing import Any

from experience_cloud.api_provider.exceptions import ApiProviderRequestError
from experience_cloud.api_provider.schemas import LogContextSchema
from experience_cloud.api_provider.services import BaseApiClient

logger = logging.getLogger(__name__)

class XByteClient(BaseApiClient):
    """Unified XByte API Client using the centralized BaseApiClient.

    Inherits retries, dynamic configuration, and API key injection.
    """

    def __init__(self, provider_code="XBYTE"):
        """Initialize the client with the XByte provider code."""
        # Initialize the base client with the specific provider code for XByte
        super().__init__(provider_code=provider_code)

    def check_logical_error(self, response) -> tuple[bool, Any, str | None]:
        """Inspect XByte's JSON payload to flag API errors that are disguised.
        
        This handles both HTTP 200 OK hidden errors (e.g., Location Not Found)
        and prevents standard HTTP 4xx/5xx responses from triggering automatic retries.
        """
        try:
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/json' in content_type:
                data = response.json()
                if not isinstance(data, dict):
                    return False, data, None
                
                # 1. Check for "msg" key (used in Invalid API Key, Missing API Key)
                if "msg" in data:
                    return True, data, str(data["msg"])
                
                # 2. Check for "message" key without "results" (e.g. Location Not Found)
                if "message" in data and not data.get("results"):
                    return True, data, str(data["message"])
                
                # 3. Sometimes they might return a statusCode != 200 inside request_log
                request_log = data.get("request_log", {})
                if isinstance(request_log, dict):
                    status_code = request_log.get("statusCode")
                    # If there's an explicit error status code inside the JSON
                    if status_code and str(status_code) != "200":
                        msg = str(data.get("message", f"XByte Error {status_code}"))
                        return True, data, msg

                return False, data, None
        except Exception:
            pass
        return False, None, None

    def fetch_results(
        self, keyword: str,
        location: str,
        platform: str,
        payload: dict[str, Any] | str | None = None,
        log_context: LogContextSchema| None = None
    ):
        """Fetch quick commerce product results from XByte API.

        Equivalent to the legacy QuickCommerceClient.fetch_results.
        """
        logger.info(f"QuickCommerce fetch → keyword={keyword}, location={location}, platform={platform}")

        # Determine specific payload structure per platform
        if payload is None:
            payload = {
                "endpoint": "result",
                "zipcode": location,
                "keyword": keyword,
                "platform": platform,
            }

        try:
            return self.post(body_type="json", body_payload=payload, log_context=log_context)

        except ApiProviderRequestError as e:
            logger.warning(f"XByte API logical/request error -> {e.message}")
            if hasattr(e, 'extra') and e.extra:
                logger.error(f"XByte API Error Body/Details: {e.extra}")
            raise
        except Exception as e:
            logger.exception("XByte unexpected error")
            raise ApiProviderRequestError(
                message="XByte API failure",
                extra=str(e)
            ) from e
