from rest_framework.response import Response

def api_response(success=True, message="", data=None, status=200, errors=None):
    """
    Unified API response format.
    Example:
        return api_response(data={"user": {...}}, message="User created")
    """
    return Response({
        "success": success,
        "message": message,
        "errors": errors,
        "data": data,
    }, status=status)
