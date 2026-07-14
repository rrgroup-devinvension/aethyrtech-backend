from rest_framework.renderers import JSONRenderer
from rest_framework.pagination import PageNumberPagination
from django.utils.timezone import now
from rest_framework.response import Response


class StandardJSONRenderer(JSONRenderer):
    """
    Wrap all DRF responses in a unified format.
    Handles standard responses and paginated responses.
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response', None)

        if response is None:
            return super().render(data, accepted_media_type, renderer_context)

        # Paginated response detection
        if isinstance(data, dict) and all(k in data for k in ["count", "results"]):
            paginated_response = {
                "success": True,
                "data": data.get("results"),
                "current_page": data.get("page", 1),
                "page_size": data.get("page_size", len(data.get("results", []))),
                "total_pages": data.get("pages", 1),
                "total": data.get("count"),
                "has_next": data.get("page", 1) < data.get("pages", 1),
                "has_previous": data.get("page", 1) > 1,
                "is_first": data.get("page", 1) == 1,
                "is_last": data.get("page", 1) >= data.get("pages", 1),
                "message": "",
                "timestamp": now()
            }
            return super().render(paginated_response, accepted_media_type, renderer_context)

        # Standard success response
        if response.status_code < 400:
            standard_response = {
                "success": True,
                "data": data,
                "message": "",
                "timestamp": now()
            }
            return super().render(standard_response, accepted_media_type, renderer_context)

        # For error responses, let exception handler handle formatting
        return super().render(data, accepted_media_type, renderer_context)

