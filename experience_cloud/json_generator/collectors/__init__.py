import logging
from collections.abc import Generator

from experience_cloud.json_generator.schemas import ProductSchema, RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator

from .karmatech_collector import get_all_karmatech_products
from .xbytes_collector import get_all_xbytes_products

logger = logging.getLogger(__name__)



def get_all_products_generator(region_data: RegionDataSchema) -> Generator[ProductSchema, None, None]:
    """Stream a unified catalog of product schemas sequentially from available databases.

    Orchestrates the sequential yielding of products across all active platforms in a region,
    ensuring each product receives a unique sequential string ID for downstream processing.
    """
    index = 1
    karmatech_called = False
    xbytes_called = False

    platforms = region_data.get("platforms", {})

    for platform in platforms.values():
        provider_code = platform.get("api_provider_code", "").lower()

        if provider_code == "karmatech" and not karmatech_called:
            for pf in get_all_karmatech_products(region_data):
                pf.id = str(index)
                index += 1
                yield pf
            karmatech_called = True

        elif provider_code == "xbytes" and not xbytes_called:
            for pf in get_all_xbytes_products(region_data):
                pf.id = str(index)
                index += 1
                yield pf
            xbytes_called = True

def get_all_products(region_data: RegionDataSchema) -> ItemGenerator:
    """Initialize a stateful iterator for streaming cross-platform product catalogs.

    Wraps the raw sequential generator in an ItemGenerator class to preserve memory efficiency
    while allowing robust downstream data pipelining and memory profiling.
    """
    return ItemGenerator(get_all_products_generator, region_data)
