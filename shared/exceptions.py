from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError, PermissionDenied, NotAuthenticated
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code

# with logging in files

from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import ValidationError, PermissionDenied, NotAuthenticated
from django.utils.timezone import now
import logging

logger = logging.getLogger(__name__)

def exception_handler(exc, context):
    """
    Custom exception handler with user-friendly messages.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        request = context.get("request")

        # Log error details
        logger.error(
            "Exception at %s: %s",
            request.path if request else "unknown path",
            str(exc),
            exc_info=True,
        )

        # 1️⃣ Handle ValidationError
        if isinstance(exc, ValidationError):
            data = response.data

            # If it's a "non_field_errors" case (like invalid credentials)
            if "non_field_errors" in data:
                message = _friendly_message(str(data["non_field_errors"][0]))
                response.data = {
                    "success": False,
                    "errorCode": "validationerror",
                    "message": message,
                    "path": request.path if request else None,
                    "timestamp": now(),
                }
            else:
                # Field-specific validation errors
                response.data = {
                    "success": False,
                    "errorCode": "validationerror",
                    "message": "Some of the data you entered is invalid. Please check and try again.",
                    "errors": data,
                    "path": request.path if request else None,
                    "timestamp": now(),
                }

        # 2️⃣ Forbidden
        elif isinstance(exc, PermissionDenied):
            response.data = {
                "success": False,
                "errorCode": "forbidden",
                "message": "You do not have permission to perform this action.",
                "path": request.path if request else None,
                "timestamp": now(),
            }

        # 3️⃣ Unauthorized
        elif isinstance(exc, NotAuthenticated):
            response.data = {
                "success": False,
                "errorCode": "unauthorized",
                "message": "You must be logged in to access this resource.",
                "path": request.path if request else None,
                "timestamp": now(),
            }

        # 4️⃣ Generic fallback
        else:
            raw_message = response.data.get("detail", str(exc))
            user_friendly_message = _friendly_message(raw_message)
            response.data = {
                "success": False,
                "errorCode": getattr(exc, "default_code", "error"),
                "message": user_friendly_message,
                "path": request.path if request else None,
                "timestamp": now(),
            }

    return response


def _friendly_message(raw_message: str) -> str:
    """
    Convert raw DRF error messages into user-friendly ones.
    """
    mapping = {
        "Invalid email or password": "The email or password you entered is incorrect.",
        "This field is required.": "Please fill out all required fields.",
        "User account is inactive": "Your account is currently disabled. Contact support.",
        "Not found.": "The requested resource could not be found.",
        "A server error occurred.": "Something went wrong on our side. Please try again later.",
        "Invalid token.": "Your session has expired. Please log in again."
    }
    return mapping.get(raw_message, raw_message)
