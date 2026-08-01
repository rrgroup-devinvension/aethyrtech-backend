from collections.abc import Mapping
from typing import Any

from django.utils.timezone import now
from rest_framework.renderers import JSONRenderer


class StandardJSONRenderer(JSONRenderer):
    """Wrap all DRF responses in a unified format.

    Handles standard responses and paginated responses.
    """

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: Mapping[str, Any] | None = None
    ) -> Any:
        """Render the response payload into JSON format.

        Args:
            data: The response data to render.
            accepted_media_type: The media type accepted by the client.
            renderer_context: Context dictionary containing request and response objects.

        Returns:
            The JSON encoded byte string of the standard or paginated response.
        """
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

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

