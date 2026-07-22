from typing import Optional
from typing_extensions import TypedDict

class DataDumpSchema(TypedDict):
    # Location details
    display_location: str
    location_id: Optional[int]
    
    # Platform details
    platform_name: str
    platform_id: Optional[int]
    platform_code: str
    
    # Keyword details
    keyword_name: str
    keyword_id: Optional[int]
    
    # Category details
    category_name: Optional[str]
    category_id: Optional[int]
    
    # API Provider details
    provider_name: str
    provider_code: str  # e.g., 'XBYTE'
    provider_id: Optional[int]
    configuration: Optional[dict]


class DataDumpResponseSchema(TypedDict):
    """
    Standardized response returned by any API Provider Service after execution.
    """
    status: str            # Must be 'success' or 'error'
    items_count: int       # The number of products fetched & saved to the DB
    message: Optional[str] # Detailed error message, or just a success note
