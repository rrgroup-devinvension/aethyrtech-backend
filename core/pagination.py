from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class DefaultPageNumberPagination(PageNumberPagination):
    """
    DRF pagination with consistent envelope. Use ?page= & ?page_size=.
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,
            "page": self.page.number,
            "pages": self.page.paginator.num_pages,
            "results": data,
        })
