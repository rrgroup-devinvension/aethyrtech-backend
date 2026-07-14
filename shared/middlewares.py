import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache

logger = logging.getLogger("django.request")

class RequestLogMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        duration = None
        if hasattr(request, "_start_time"):
            duration = round(time.time() - request._start_time, 3)

        logger.info(
            "[%s] %s %s %s %ss",
            request.method,
            response.status_code,
            request.get_full_path(),
            request.user if hasattr(request, "user") and request.user.is_authenticated else "Anonymous",
            duration or "-",
        )
        return response

class IdempotencyMiddleware(MiddlewareMixin):
    def process_request(self, request):
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
        if hasattr(request, "_idempotency_key") and response.status_code < 400:
            # Cache the successful response for 24 hours
            cache.set(request._idempotency_key, response, timeout=86400)
        return response
