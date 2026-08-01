from typing import Any, Literal, TypedDict


class RegionSchema(TypedDict):
    """Schema for regional metadata passed down during execution."""
    region_id: int | None
    region_name: str | None
    brand_id: int | None
    brand_name: str | None

class LogContextSchema(TypedDict, total=False):
    """Type definition for the context dictionary passed to the API logger.

    Provides optional metadata like related models, IDs, and usage costs.
    """
    platform_id: int | None
    category_id: int | None
    keyword_name: str | None
    location_name: str | None
    regions: list[RegionSchema] | None
    cost: float | None
    products_found: int | None


class DynamicRequestSchema(TypedDict):
    """Schema for a fully rendered dynamic request payload."""
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    endpoint: str
    query_params: dict[str, Any]
    headers: dict[str, str]
    body_type: Literal["json", "form-data", "raw"]
    body_payload: dict[str, Any] | str
