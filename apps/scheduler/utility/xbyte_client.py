import requests
import logging
from django.conf import settings
from apps.scheduler.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)


class XByteClient:
    """
    Unified XByte API Client

    Supports:
    - input
    - result
    - delete
    - check_input

    Provides:
    - centralized config
    - uniform error handling
    - clean logging
    """

    def __init__(self):
        self.base_url = getattr(settings, "XBYTE_API_URL", '') 
        self.api_key = getattr(settings, "XBYTE_API_KEY", '')  
        self.timeout = getattr(settings, "TIMEOUT", 30)

        if not self.base_url or not self.api_key:
            raise ExternalAPIException(
                message="XByte API configuration missing",
                extra="BASE_URL or API_KEY not set"
            )

    # =====================================================
    # CORE REQUEST HANDLER
    # =====================================================

    def _post(self, payload):
        payload["api_key"] = self.api_key

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=self.timeout
            )

            try:
                data = response.json()
            except Exception:
                raise ExternalAPIException(
                    message="Invalid JSON response from XByte",
                    extra=response.text
                )

            # HTTP error
            if response.status_code >= 400:
                raise ExternalAPIException(
                    message=data.get("message") or "XByte API HTTP error",
                    extra=data
                )

            # Logical API error
            if data.get("message") and not data.get("results"):
                raise ExternalAPIException(
                    message=data.get("message"),
                    extra=data
                )

            return data

        except requests.Timeout:
            raise ExternalAPIException(
                message="XByte API timeout",
                extra="Request timed out"
            )

        except requests.ConnectionError as e:
            raise ExternalAPIException(
                message="XByte connection error",
                extra=str(e)
            )

        except requests.RequestException as e:
            raise ExternalAPIException(
                message="XByte request failed",
                extra=str(e)
            )

    def input(self, zipcode, keywords_list, platform):

        if platform in ["noon_ksa"]:
            print("XBYTE API: Sending brand_input request for keywords:", keywords_list[0])
            return self._post({
                "endpoint": "brand_input",
                "zipcode": zipcode,
                "frequency": "bi-weekly",
                "brand_keywords_list": list(keywords_list),
                "platform": platform
                
            })
        
        print("XBYTE API: Sending input request for platform:", platform)

        return self._post({
            "endpoint": "input",
            "zipcode": zipcode,
            "keywords_list": list(keywords_list),
        })
        

    def result(self, zipcode, keyword, platform):
        if platform in ["noon_ksa"]:
            print("XBYTE API: Sending brand_result request for keyword:", keyword)
            return self._post({
                "endpoint": "brand_result",
                "zipcode": zipcode,
                "brand_keyword": keyword,
                "platform": platform,
            })
        return self._post({
            "endpoint": "result",
            "zipcode": zipcode,
            "keyword": keyword,
            "platform": platform,
        })

    def delete(self, zipcode, keywords_list):
        return self._post({
            "endpoint": "delete",
            "zipcode": zipcode,
            "keywords_list": list(keywords_list),
        })

    def check_input(self, zipcode, keyword):
        return self._post({
            "endpoint": "check_input",
            "zipcode": zipcode,
            "keyword": keyword,
        })