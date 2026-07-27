import logging
from typing import Generator
from experience_cloud.json_generator.utils import ItemGenerator
from experience_cloud.json_generator.schemas import ProductSchema
from experience_cloud.json_generator.schemas import RegionDataSchema
from .karmatech_collector import get_all_karmatech_products
from .xbytes_collector import get_all_xbytes_products

logger = logging.getLogger(__name__)



def get_all_products_generator(region_data: RegionDataSchema) -> Generator[ProductSchema, None, None]:
    index = 1
    karmatech_called = False
    xbytes_called = False
    
    platforms = region_data.get("platforms", {})
    
    for platform in platforms.values():
        provider_code = platform.get("api_provider_code", "").lower()
        
        if provider_code == "karmatech" and not karmatech_called:
            for pf in get_all_karmatech_products(region_data):
                pf.id = index
                index += 1
                yield pf
            karmatech_called = True
            
        elif provider_code == "xbytes" and not xbytes_called:
            for pf in get_all_xbytes_products(region_data):
                pf.id = index
                index += 1
                yield pf
            xbytes_called = True

def get_all_products(region_data: RegionDataSchema) -> ItemGenerator:
    return ItemGenerator(get_all_products_generator, region_data)
