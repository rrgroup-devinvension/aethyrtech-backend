import json
import logging
import time
from typing import Any, Literal, cast

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from requests.auth import HTTPBasicAuth

from .exceptions import ApiProviderConfigurationError, ApiProviderRequestError
from .models import ApiProvider, APIUsageLog, APIUsageSummary, AuthType
from .schemas import DynamicRequestSchema, LogContextSchema

logger = logging.getLogger(__name__)

class BaseApiClient:
    """A powerful, centralized HTTP client engine powered by the ApiProvider model.

    It handles base URLs, dynamic headers, authentication injection, timeouts, and retries natively.
    """

    def __init__(self, provider_code: str | None = None, provider: ApiProvider | None = None):
        """Initialize BaseApiClient."""
        if provider:
            self.provider = provider
            self.provider_code = provider.code or "TEST_PROVIDER"
        elif provider_code:
            self.provider_code = provider_code
            try:
                self.provider = ApiProvider.objects.get(code=self.provider_code)
            except ObjectDoesNotExist as e:
                raise ApiProviderConfigurationError(
                    f"ApiProvider with code '{self.provider_code}' does not exist."
                ) from e
        else:
            raise ValueError("Must provide either provider_code or provider")

        if self.provider.status != "ACTIVE":
            raise ApiProviderConfigurationError(f"ApiProvider '{self.provider_code}' is not ACTIVE.")

        self.base_url = self.provider.base_url.rstrip("/")
        self.timeout = self.provider.timeout
        self.retry_count = self.provider.retry_count
        self.retry_delay = self.provider.retry_delay

        # Build the session
        self.session = requests.Session()

        # 1. Apply Default Headers
        if isinstance(self.provider.default_headers, dict):
            self.session.headers.update(self.provider.default_headers)

        # 2. Apply Authentication
        self._apply_authentication()

    def _apply_authentication(self):
        auth_type = self.provider.auth_type
        creds = self.provider.get_decrypted_credentials()

        if auth_type == AuthType.BEARER:
            token = creds.get('token', '')
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})

        elif auth_type == AuthType.BASIC:
            username = creds.get('username', '')
            password = creds.get('password', '')
            self.session.auth = HTTPBasicAuth(username, password)

        elif auth_type == AuthType.API_KEY:
            # Note: API_KEY usually goes in headers or params.
            # If it needs to go in the payload (like XByte), we handle it during the request execution.
            api_key = creds.get('api_key', '')
            key_name = creds.get('key_name', 'X-Api-Key')
            location = creds.get('location', 'header') # header, query, or payload

            self._api_key_value = api_key
            self._api_key_name = key_name
            self._api_key_location = location

            if location == 'header' and api_key:
                self.session.headers.update({key_name: api_key})

        elif auth_type == AuthType.OAUTH2:
            token_url = creds.get('token_url')
            client_id = creds.get('client_id')
            client_secret = creds.get('client_secret')
            scope = creds.get('scope', '')

            if token_url and client_id and client_secret:
                data = {'grant_type': 'client_credentials'}
                if scope:
                    data['scope'] = scope
                try:
                    resp = requests.post(token_url, data=data, auth=(client_id, client_secret), timeout=10)
                    resp.raise_for_status()
                    token = resp.json().get('access_token')
                    if token:
                        self.session.headers.update({"Authorization": f"Bearer {token}"})
                except (requests.RequestException, ValueError) as e:
                    logger.error(f"[{self.provider_code}] Failed to fetch OAuth2 token: {e}")

        elif auth_type == AuthType.JWT:
            import datetime

            import jwt
            private_key = creds.get('private_key', '')
            algorithm = creds.get('algorithm', 'HS256')
            payload = creds.get('payload', {})
            header_name = creds.get('header_name', 'Authorization')
            header_prefix = creds.get('header_prefix', 'Bearer ')

            if private_key:
                if 'exp' not in payload:
                    payload['exp'] = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)

                try:
                    token = jwt.encode(payload, private_key, algorithm=algorithm)
                    if isinstance(token, bytes):
                        token = token.decode('utf-8')
                    self.session.headers.update({header_name: f"{header_prefix}{token}"})
                except (ValueError, TypeError, jwt.PyJWTError) as e:
                    logger.error(f"[{self.provider_code}] Failed to encode JWT: {e}")

        elif auth_type == AuthType.CUSTOM:
            headers = creds.get('headers', {})
            payload = creds.get('payload', {})

            if headers:
                self.session.headers.update(headers)
            if payload:
                self._custom_payload = payload

    def check_logical_error(self, response: requests.Response) -> tuple[bool, Any, str | None]:
        """Override this in subclasses to check for logical errors in the response.

        This runs before HTTP raise_for_status() to allow parsing JSON errors in 4xx/5xx
        responses and treating them as permanent failures instead of retrying them.

        Returns:
            tuple: (is_error, parsed_data, error_message)
        """
        return False, None, None

    def _log_usage(
        self,
        status: str,
        response_time: float,
        request_size: int = 0,
        response_size: int = 0,
        log_context: LogContextSchema | None = None,
        error_message: str | None = None
    ):
        if not self.provider.pk:
            logger.info(f"[{self.provider_code}] Skipping log usage because provider is not saved in database.")
            return

        if not log_context:
            log_context = {}

        # 1. Handle Regions & Cost Splitting
        regions = log_context.get('regions', [])
        split_cost = 0.0

        kw_name = log_context.get('keyword_name') or ''
        loc_name = log_context.get('location_name') or ''
        platform_id = log_context.get('platform_id')
        category_id = log_context.get('category_id')

        # If no regions, log at least one entry for the general request
        if not regions:
            APIUsageLog.objects.create(
                api_provider=self.provider,
                status=status,
                response_time=response_time,
                request_size=request_size,
                response_size=response_size,
                platform_id=platform_id,
                category_id=category_id,
                keyword_name=kw_name,
                location_name=loc_name,
                cost=split_cost,
                error_message=error_message or ''
            )
        else:
            brand_ids = ",".join([str(r.get('brand_id')) for r in regions if r.get('brand_id')])
            brand_names = ",".join([str(r.get('brand_name')) for r in regions if r.get('brand_name')])
            region_ids = ",".join([str(r.get('region_id')) for r in regions if r.get('region_id')])
            region_names = ",".join([str(r.get('region_name')) for r in regions if r.get('region_name')])

            APIUsageLog.objects.create(
                api_provider=self.provider,
                status=status,
                response_time=response_time,
                request_size=request_size,
                response_size=response_size,
                platform_id=platform_id,
                category_id=category_id,
                keyword_name=kw_name,
                location_name=loc_name,
                brand_ids=brand_ids,
                brand_names=brand_names,
                region_ids=region_ids,
                region_names=region_names,
                cost=split_cost,
                error_message=error_message or ''
            )

        # 2. Update Daily Summary per region
        today = timezone.now().date()
        from decimal import Decimal

        if not regions:
            summary, _created = APIUsageSummary.objects.get_or_create(
                api_provider=self.provider,
                date=today,
                platform_id=platform_id,
                brand_id=None,
                region_id=None,
                defaults={
                    'brand_name': '',
                    'region_name': '',
                    'total_calls': 0,
                    'success_calls': 0,
                    'failed_calls': 0,
                    'average_response_time': 0.0,
                    'total_products': 0,
                    'total_cost': 0.0
                }
            )
            total_time = (summary.average_response_time * summary.total_calls) + response_time
            summary.total_calls += 1
            if status == 'SUCCESS':
                summary.success_calls += 1
                summary.total_products += (log_context.get('products_found') or 0)
            else:
                summary.failed_calls += 1
            summary.average_response_time = total_time / summary.total_calls
            summary.total_cost = Decimal(str(summary.total_cost)) + Decimal(str(split_cost))
            summary.save()
        else:
            for region in regions:
                summary, _created = APIUsageSummary.objects.get_or_create(
                    api_provider=self.provider,
                    date=today,
                    platform_id=platform_id,
                    brand_id=region.get('brand_id'),
                    region_id=region.get('region_id'),
                    defaults={
                        'brand_name': region.get('brand_name') or '',
                        'region_name': region.get('region_name') or '',
                        'total_calls': 0,
                        'success_calls': 0,
                        'failed_calls': 0,
                        'average_response_time': 0.0,
                        'total_products': 0,
                        'total_cost': 0.0
                    }
                )
                total_time = (summary.average_response_time * summary.total_calls) + response_time
                summary.total_calls += 1
                if status == 'SUCCESS':
                    summary.success_calls += 1
                    summary.total_products += (log_context.get('products_found') or 0)
                else:
                    summary.failed_calls += 1
                summary.average_response_time = total_time / summary.total_calls
                summary.total_cost = Decimal(str(summary.total_cost)) + Decimal(str(split_cost))
                summary.save()

    def render_template(self, data, variables: dict):
        """Recursively replaces {{variable_name}} with actual values in a dict/list/string."""
        import re
        if isinstance(data, str):
            def replacer(match):
                var_name = match.group(1)
                return str(variables.get(var_name, match.group(0)))
            return re.sub(r'\{\{([^}]+)\}\}', replacer, data)
        elif isinstance(data, dict):
            return {k: self.render_template(v, variables) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.render_template(item, variables) for item in data]
        return data

    def prepare_body(
        self, config_body: dict, variables: dict
    ) -> tuple[Literal["json", "form-data", "raw"], dict[str, Any] | str]:
        """Renders the body configuration."""
        rendered = self.render_template(config_body, variables)
        body_type = cast(Literal["json", "form-data", "raw"], rendered.get("type", "json"))
        body_payload = rendered.get("payload", {})
        return body_type, body_payload

    def prepare_headers(self, config_headers: dict, variables: dict) -> dict:
        """Renders the headers configuration."""
        return self.render_template(config_headers, variables)

    def prepare_query_params(self, config_query: dict, variables: dict) -> dict:
        """Renders the query parameters configuration."""
        return self.render_template(config_query, variables)

    def prepare_endpoint(self, endpoint: str, path_variables: dict, variables: dict) -> str:
        """Renders the endpoint string and injects any path variables."""
        # First render the path variables block
        rendered_paths = self.render_template(path_variables, variables)
        # Then render the endpoint string using those specific path variables (or general variables)
        context = {**variables, **rendered_paths}
        return self.render_template(endpoint, context)

    def prepare_dynamic_request(self, config: dict, variables: dict) -> DynamicRequestSchema:
        """Dynamically build an API call schema by orchestrating the helper methods."""
        request_config = config.get("request", {})
        if not request_config:
            raise ValueError("No 'request' block found in dynamic configuration")

        method = cast(Literal["GET", "POST", "PUT", "PATCH", "DELETE"], request_config.get("method", "GET"))

        endpoint = self.prepare_endpoint(
            request_config.get("endpoint", ""),
            request_config.get("path_variables", {}),
            variables
        )

        query_params = self.prepare_query_params(
            request_config.get("query_params", {}),
            variables
        )

        headers = self.prepare_headers(
            request_config.get("headers", {}),
            variables
        )

        body_type, body_payload = self.prepare_body(
            request_config.get("body", {}),
            variables
        )

        return {
            "method": method,
            "endpoint": endpoint,
            "query_params": query_params,
            "headers": headers,
            "body_type": body_type,
            "body_payload": body_payload,
        }

    def request(
        self,
        method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
        endpoint: str = "",
        query_params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body_type: Literal["json", "form-data", "raw"] = "json",
        body_payload: dict[str, Any] | str | None = None,
        log_context: LogContextSchema | None = None,
        **kwargs
    ):
        """Execute an HTTP request with built-in retries, timeouts, and error handling.

        Accepts explicit parameters (query_params, headers, body_payload)
        and automatically maps them to the underlying requests library.
        Returns the raw `requests.Response` object, or automatically parsed JSON if appropriate.
        """
        if query_params:
            kwargs["params"] = query_params
        if headers:
            kwargs["headers"] = headers
        if body_payload is not None:
            if body_type == "json":
                kwargs["json"] = body_payload
            else:
                kwargs["data"] = body_payload
        url = self.base_url
        if endpoint:
            if not endpoint.startswith("/"):
                endpoint = "/" + endpoint
            url = f"{self.base_url}{endpoint}"

        # Handle Payload and Query API Keys
        if self.provider.auth_type == AuthType.API_KEY:
            loc = getattr(self, '_api_key_location', '')
            if loc == 'payload':
                if 'json' in kwargs and isinstance(kwargs['json'], dict):
                    kwargs['json'][self._api_key_name] = self._api_key_value
                elif 'data' in kwargs and isinstance(kwargs['data'], dict):
                    kwargs['data'][self._api_key_name] = self._api_key_value
            elif loc == 'query':
                # Ensure params dict exists
                kwargs.setdefault('params', {})
                if isinstance(kwargs['params'], dict):
                    kwargs['params'][self._api_key_name] = self._api_key_value

        # Handle CUSTOM payload
        if hasattr(self, '_custom_payload') and self._custom_payload:
            if 'json' in kwargs and isinstance(kwargs['json'], dict):
                kwargs['json'].update(self._custom_payload)
            elif 'data' in kwargs and isinstance(kwargs['data'], dict):
                kwargs['data'].update(self._custom_payload)

        kwargs.setdefault('timeout', self.timeout)

        last_exception = None

        for attempt in range(self.retry_count + 1):
            start_time = time.time()
            request_size = 0

            # Estimate request size
            if 'json' in kwargs:
                request_size = len(json.dumps(kwargs['json']).encode('utf-8'))
            elif 'data' in kwargs and isinstance(kwargs['data'], str):
                request_size = len(kwargs['data'].encode('utf-8'))

            try:
                # Mask credentials in logs
                masked_url = url
                if hasattr(self, '_api_key_value') and self._api_key_value:
                    masked_url = masked_url.replace(self._api_key_value, "********")

                logger.info(f"[{self.provider_code}] {method.upper()} {masked_url} (Attempt {attempt + 1})")
                response = self.session.request(method, url, **kwargs)

                response_time = time.time() - start_time
                response_size = len(response.content) if response.content else 0

                # Check for Logical Errors first (this handles both 200 OK errors and parses JSON for 4xx/5xx)
                is_logical_error, parsed_data, error_message = self.check_logical_error(response)

                if is_logical_error:
                    self._log_usage(
                        'FAILED', response_time, request_size, response_size, log_context, error_message=error_message
                    )
                    raise ApiProviderRequestError(
                        message=error_message or "API Logical Error",
                        extra=parsed_data if parsed_data else error_message
                    )

                # Check for unhandled HTTP errors
                response.raise_for_status()

                self._log_usage('SUCCESS', response_time, request_size, response_size, log_context)

                # Return parsed data if the logical checker already parsed it
                if parsed_data is not None:
                    return parsed_data

                # Check if JSON is expected (REST/GraphQL usually use JSON)
                content_type = response.headers.get('Content-Type', '').lower()
                if 'application/json' in content_type:
                    return response.json()

                # For SOAP/XML or Raw Text, return text
                if 'text/' in content_type or 'xml' in content_type:
                    return response.text

                # For binary/other files
                return f"[Binary Data/File: {content_type}]"

            except requests.exceptions.RequestException as e:
                last_exception = e
                response_time = time.time() - start_time
                response_size = (
                    len(e.response.content)
                    if hasattr(e, 'response') and e.response and e.response.content
                    else 0
                )
                logger.warning(f"[{self.provider_code}] Request failed: {e}")

                if attempt < self.retry_count:
                    logger.info(f"[{self.provider_code}] Retrying in {self.retry_delay} seconds...")
                    self._log_usage('RETRY', response_time, request_size, response_size, log_context)
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"[{self.provider_code}] Max retries ({self.retry_count}) reached.")

                    # Extract detailed error message if available
                    error_msg_body = str(e)
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_msg_body = str(e.response.json())
                        except ValueError:
                            error_msg_body = e.response.text or str(e)

                    self._log_usage(
                        'FAILED', response_time, request_size, response_size, log_context, error_message=error_msg_body
                    )

        # If we exit the loop, raise the last exception
        extra = {}
        if last_exception is not None and hasattr(last_exception, 'response') and last_exception.response is not None:
            status_code = last_exception.response.status_code
            extra = {'status_code': status_code, 'body': last_exception.response.text}

            # Basic Circuit Breaker: If the server is completely down (502/503/504), mark provider as DOWN
            if status_code in [502, 503, 504]:
                logger.error(f"[{self.provider_code}] Circuit Breaker tripped! Marking provider DOWN.")
                self.provider.health_check_status = f"DOWN (HTTP {status_code})"
                self.provider.save(update_fields=['health_check_status'])

        raise ApiProviderRequestError(
            message=f"[{self.provider_code}] API request failed: {last_exception!s}",
            extra=extra
        )

    def get(self, endpoint: str = "", log_context: LogContextSchema | None = None, **kwargs):
        """Make a GET request."""
        return self.request("GET", endpoint, log_context=log_context, **kwargs)

    def post(self, endpoint: str = "", log_context: LogContextSchema | None = None, **kwargs):
        """Make a POST request."""
        return self.request("POST", endpoint, log_context=log_context, **kwargs)

    def put(self, endpoint: str = "", log_context: LogContextSchema | None = None, **kwargs):
        """Make a PUT request."""
        return self.request("PUT", endpoint, log_context=log_context, **kwargs)

    def delete(self, endpoint: str = "", log_context: LogContextSchema | None = None, **kwargs):
        """Make a DELETE request."""
        return self.request("DELETE", endpoint, log_context=log_context, **kwargs)
