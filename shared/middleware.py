import time
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("django.request")

class RequestLogMiddleware(MiddlewareMixin):
    """
    Logs each request with method, path, status, and execution time.
    Add to settings.MIDDLEWARE after authentication.
    """

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
