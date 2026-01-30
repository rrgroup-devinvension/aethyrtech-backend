import logging
from datetime import datetime
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import match_brand
logger = logging.getLogger(__name__)

def get_catalog_list(products, brand_name, is_competitor=False):
    return [
        p.to_catalog_json(is_competitor)
        for p in products
        if match_brand(p.brand, brand_name)
    ]

def catalog_data_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template="catalog", platform_type=None):
    logger.info(f"Starting CATALOG JSON build | Task={task.id}")
    try:
        payload = {}
        payload[brands[0]] = get_catalog_list(products, brand_name, False)
        for b in brands[1:]:
            payload[b] = get_catalog_list(products, b, True)
        logger.info(f"Completed CATALOG JSON build | Task={task.id}")
        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except SchedulerBaseException:
        raise
    except Exception as exc:
        logger.exception("Catalog JSON build failed")
        raise DataProcessingException(
            message="Catalog JSON build failed",
            extra=str(exc)
        )
