from experience_cloud.json_generator.decorators import handle_builder_exceptions
from typing import Dict
from experience_cloud.executions.models import JsonFileTask
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator
import logging

from datetime import datetime
from experience_cloud.json_generator.exceptions import SchedulerBaseException, DataProcessingException
from experience_cloud.json_generator.utils import match_brand
logger = logging.getLogger(__name__)

@handle_builder_exceptions
def catalog_builder(region_data: RegionDataSchema, task, products=None, template="template-name") -> tuple[bool, dict]:
    brands = region_data.get("display_brands", [])
    keywords = region_data.get("keywords", [])
    brand_id = region_data.get("brand_id")
    brand_name = region_data.get("brand_name")
    platform_type = region_data.get("platform_type", [])

    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting CATALOG JSON build | Task={t_id}")
    payload = {b: [] for b in brands}
    
    for p in products:
        if not p.brand:
            continue
            
        matched_brand = None
        is_competitor = True
        
        if match_brand(brand_name, p.brand):
            matched_brand = brands[0]
            is_competitor = False
        else:
            for b in brands[1:]:
                if match_brand(b, p.brand):
                    matched_brand = b
                    break
                    
        if matched_brand:
            payload[matched_brand].append(p.to_catalog_json(matched_brand, is_competitor))
    logger.info(f"Completed CATALOG JSON build | Task={t_id}")
    return False, payload
