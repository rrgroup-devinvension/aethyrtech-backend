import logging
from datetime import datetime
from apps.scheduler.json_builder.utils import save_json_to_file
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import match_brand
logger = logging.getLogger(__name__)
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

def get_catalog_list(products, brand_name, is_competitor=False):
    return [
        p.to_catalog_json(is_competitor)
        for p in products
        if match_brand(p.brand, brand_name)
    ]

def catalog_data_builder(brands, keywords, products, task, brand_id=None, brand_name=None, template="catalog", platform_type=None):
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"Starting CATALOG JSON build | Task={t_id}")
    try:
        log_start(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        payload = {}
        payload[brands[0]] = get_catalog_list(products, brand_name, False)
        for b in brands[1:]:
            payload[b] = get_catalog_list(products, b, True)
        logger.info(f"Completed CATALOG JSON build | Task={t_id}")
        log_success(task_id=t_id, info={'template': template, 'brand_id': brand_id})
        return save_json_to_file(task, payload, brand_id, brand_name, template)
    except SchedulerBaseException:
        raise
    except Exception as exc:
        logger.exception("Catalog JSON build failed")
        log_error(task_id=t_id, error=str(exc), extra={'template': template, 'brand_id': brand_id})
        raise DataProcessingException(
            message="Catalog JSON build failed",
            extra=str(exc)
        )
