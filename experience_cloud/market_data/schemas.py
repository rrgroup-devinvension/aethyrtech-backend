
from typing_extensions import TypedDict


class RegionSchema(TypedDict):
    """Schema for regional metadata passed down during execution."""
    region_id: int | None
    region_name: str | None
    brand_id: int | None
    brand_name: str | None

class DataDumpSchema(TypedDict):
    """Schema for data dump execution context."""
    # Location details
    display_location: str

    # Platform details
    platform_name: str
    platform_id: int | None
    platform_code: str

    # Keyword details
    keyword_name: str

    # Category details
    category_name: str | None
    category_id: int | None

    # Regional Details
    regions: list[RegionSchema]

    # API Provider details
    provider_name: str
    provider_code: str  # e.g., 'XBYTE'
    provider_id: int | None
    configuration: dict | None


class DataDumpResponseSchema(TypedDict):
    """Standardized response returned by any API Provider Service after execution."""
    status: str            # Must be 'success' or 'error'
    items_count: int       # The number of products fetched & saved to the DB
    message: str | None # Detailed error message, or just a success note
