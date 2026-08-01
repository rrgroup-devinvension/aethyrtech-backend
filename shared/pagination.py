from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response


class EnterpriseOffsetPagination(PageNumberPagination):
    """Standard Offset/Page-based pagination.

    Use this for small datasets or admin dashboards where jumping to a specific page is required.
    """
    page_size = 20
    page_size_query_param = "size"
    max_page_size = 200

    def paginate_queryset(self, queryset, request, view=None):
        """Override to return an empty list instead of 404 on invalid page."""
        from rest_framework.exceptions import NotFound
        try:
            return super().paginate_queryset(queryset, request, view=view)
        except NotFound:
            # If the page is out of bounds, simulate an empty page
            page_size = self.get_page_size(request) or self.page_size or 20
            paginator = self.django_paginator_class(queryset, page_size)
            page_number = request.query_params.get(self.page_query_param, 1)
            from django.core.paginator import Page
            self.page = Page([], page_number, paginator)
            self.request = request
            return []

    def get_paginated_response(self, data):
        """Format the response payload with pagination metadata."""
        assert self.page is not None, "paginate_queryset must be called before get_paginated_response"
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "pages": self.page.paginator.num_pages,
            "page_size": self.page.paginator.per_page,
            "results": data,
        })

class EnterpriseCursorPagination(CursorPagination):
    """Enterprise Cursor-based pagination.

    O(1) performance for deep pagination on massive datasets (e.g., Millions of Market Data rows).
    Prevents duplicate/skipped records during real-time inserts.
    """
    page_size = 50
    page_size_query_param = "size"
    cursor_query_param = "cursor"
    ordering = "-created_at"  # Default ordering, must be indexed in DB for true O(1) performance
