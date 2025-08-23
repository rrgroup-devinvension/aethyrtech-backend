from rest_framework.exceptions import APIException


class AppError(APIException):
    """
    A predictable, first-class application error you can raise anywhere.
    """
    status_code = 400
    default_detail = "An application error occurred."
    default_code = "app_error"
