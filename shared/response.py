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
                "currentPage": data.get("page", 1),
                "pageSize": data.get("page_size", len(data.get("results", []))),
                "totalPages": (data.get("count") + data.get("page_size", 25) - 1) // data.get("page_size", 25),
                "total": data.get("count"),
                "hasNext": data.get("next") is not None,
                "hasPrevious": data.get("previous") is not None,
                "isFirst": data.get("previous") is None,
                "isLast": data.get("next") is None,
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


class StandardResultsSetPagination(PageNumberPagination):
    """
    Unified paginated response.
    """
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "data": data,
            "currentPage": self.page.number,
            "pageSize": self.page.paginator.per_page,
            "totalPages": self.page.paginator.num_pages,
            "total": self.page.paginator.count,
            "hasNext": self.page.has_next(),
            "hasPrevious": self.page.has_previous(),
            "isFirst": self.page.number == 1,
            "isLast": self.page.number == self.page.paginator.num_pages,
            "message": "",
            "timestamp": now()
        })
