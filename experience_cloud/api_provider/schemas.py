from typing import TypedDict, Optional

class LogContextSchema(TypedDict, total=False):
    platform_id: Optional[int]
    category_id: Optional[int]
    keyword_id: Optional[int]
    location_id: Optional[int]
    brand_id: Optional[int]
    brand_name: Optional[str]
    region_id: Optional[int]
    cost: Optional[float]
    products_found: Optional[int]
