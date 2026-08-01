import contextlib
import json
import logging
import time

from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("django.request")


class RequestLogMiddleware(MiddlewareMixin):
    """Log all requests and their durations, including error payloads."""

    def process_request(self, request):
        """Record the start time and safely read the request body."""
        request._start_time = time.time()
        # Read body early if needed for error logging later, but safely
        # Note: reading request.body can sometimes interfere with stream parsers,
        # but DRF usually handles it fine. For extreme safety in Django,
        # we try to get it, but catch exceptions.
        try:
            request._req_body = request.body
        except Exception:  # noqa: BLE001
            request._req_body = b""

    def process_response(self, request, response):
        """Calculate duration and log the request/response details."""
        duration = None
        if hasattr(request, "_start_time"):
            duration = round(time.time() - request._start_time, 3)

        status_code = response.status_code
        user = request.user if hasattr(request, "user") and request.user.is_authenticated else "Anonymous"

        log_msg = f"[{request.method}] {status_code} {request.get_full_path()} {user} {duration or '-'}s"

        if status_code >= 400:
            # On error, log request and response payloads for debugging
            req_body = getattr(request, "_req_body", b"")
            try:
                # Mask passwords if present
                if req_body:
                    req_data = json.loads(req_body.decode('utf-8'))
                    if 'password' in req_data:
                        req_data['password'] = '***MASKED***'  # noqa: S105
                    if 'token' in req_data:
                        req_data['token'] = '***MASKED***'  # noqa: S105
                    req_body_str = json.dumps(req_data)
                else:
                    req_body_str = ""
            except (ValueError, TypeError):
                req_body_str = req_body.decode('utf-8', errors='replace')

            res_body_str = ""
            if hasattr(response, 'content'):
                with contextlib.suppress(UnicodeDecodeError, AttributeError):
                    res_body_str = response.content.decode('utf-8', errors='replace')

            logger.error(f"{log_msg} | Req: {req_body_str} | Res: {res_body_str}")
        else:
            logger.info(log_msg)

        return response

class IdempotencyMiddleware(MiddlewareMixin):
    """Ensure safe retries for state-mutating requests using Idempotency-Key headers."""

    def process_request(self, request):
        """Return a cached response if an Idempotency-Key matches an existing successful request."""
        if request.method not in ["POST", "PATCH", "PUT"]:
            return None

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return None

        cache_key = f"idempotency:{idempotency_key}"
        cached_response = cache.get(cache_key)

        if cached_response:
            # Return the exact cached HTTP response
            return cached_response

        # Store for response phase
        request._idempotency_key = cache_key
        return None

    def process_response(self, request, response):
        """Cache successful state-mutating responses tied to an Idempotency-Key."""
        if hasattr(request, "_idempotency_key") and response.status_code < 400:
            # Cache the successful response for 24 hours
            cache.set(request._idempotency_key, response, timeout=86400)
        return response
