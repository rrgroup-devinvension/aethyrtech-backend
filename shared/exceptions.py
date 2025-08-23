from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status


class APIError(Exception):
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code


def exception_handler(exc, context):
    if isinstance(exc, APIError):
        return Response(
            {"detail": exc.message},
            status=exc.status_code
        )
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response
    return Response({"detail": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
