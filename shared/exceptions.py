from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied, NotAuthenticated
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code

def custom_exception_handler(exc, context):
    """
    Custom exception handler that guarantees { status: "error", message: "...", errors: [...] } format.
    """
    response = drf_exception_handler(exc, context)

    if response is not None:
        request = context.get("request")
        logger.error(
            "Exception at %s: %s",
            request.path if request else "unknown path",
            str(exc),
            exc_info=True,
        )

        data = response.data
        formatted_data = {
            "success": False,
            "message": "An error occurred.",
            "errors": []
        }

        if isinstance(exc, ValidationError):
            formatted_data["message"] = "Validation failed."
            if isinstance(data, dict):
                for field, errors in data.items():
                    if isinstance(errors, list):
                        for error in errors:
                            formatted_data["errors"].append({"field": field, "message": str(error)})
                    else:
                        formatted_data["errors"].append({"field": field, "message": str(errors)})
            elif isinstance(data, list):
                for error in data:
                    formatted_data["errors"].append({"field": "non_field_errors", "message": str(error)})

        elif isinstance(exc, PermissionDenied):
            formatted_data["message"] = "You do not have permission to perform this action."

        elif isinstance(exc, NotAuthenticated):
            formatted_data["message"] = "You must be logged in to access this resource."

        else:
            raw_message = data.get("detail", str(exc))
            formatted_data["message"] = str(raw_message)

        response.data = formatted_data

    return response
