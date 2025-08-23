from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status
from django.utils.timezone import now

class APIError(Exception):
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code

# with logging in files
def exception_handler(exc, context):
    """
    Returns error response in the required format.
    """
    response = drf_exception_handler(exc, context)
    if response is not None:
        request = context.get('request')
        response.data = {
            "success": False,
            "errorCode": getattr(exc, 'default_code', 'error'),
            "message": response.data.get('detail', str(exc)),
            "path": request.path if request else None,
            "timestamp": now()
        }

    return response