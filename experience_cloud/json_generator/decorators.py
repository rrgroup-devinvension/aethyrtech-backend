import logging
from functools import wraps

from rest_framework.exceptions import NotFound

from experience_cloud.json_generator.exceptions import DataProcessingException, SchedulerBaseException

logger = logging.getLogger(__name__)


def handle_builder_exceptions(func):
    """Wrap JSON generator builder functions to intercept, standardize, and log unexpected data processing errors.

    Transforms underlying structural or API dependency exceptions (like NotFound) into standardized
    DataProcessingException instances with embedded brand and template context.
    """

    @wraps(func)
    def wrapper(region_data, task, template, products=None, *args, **kwargs):
        # We accept 'products' optionally to support both Core (which sends products)
        # and Insight builders (which do not need products, though Orchestrator might send it)
        try:
            if products is not None:
                return func(*args, region_data=region_data, task=task, template=template, products=products, **kwargs)
            else:
                return func(*args, region_data=region_data, task=task, template=template, **kwargs)
        except SchedulerBaseException:
            raise
        except NotFound as nf_exc:
            brand_id = "unknown"
            brand_name = "unknown"
            if isinstance(region_data, dict):
                brand_id = region_data.get("brand_id", brand_id)
                brand_name = region_data.get("brand_name", brand_name)

            error_msg = f"Dependency missing: {nf_exc!s}. First generate required JSON file."
            logger.warning(f"Insight build failed due to missing dependency for {template}: {nf_exc!s}")

            raise DataProcessingException(
                message=error_msg,
                extra={"brand_id": brand_id, "brand_name": brand_name, "template": template, "error": str(nf_exc)},
            ) from nf_exc
        except Exception as exc:
            brand_id = "unknown"
            brand_name = "unknown"

            if isinstance(region_data, dict):
                brand_id = region_data.get("brand_id", brand_id)
                brand_name = region_data.get("brand_name", brand_name)
            else:
                try:
                    brand_id = region_data.get("brand_id", brand_id)
                    brand_name = region_data.get("brand_name", brand_name)
                except (AttributeError, TypeError):
                    pass

            logger.exception(f"JSON build failed for template: {template}")
            raise DataProcessingException(
                message=f"JSON build failed for template: {template}",
                extra={"brand_id": brand_id, "brand_name": brand_name, "template": template, "error": str(exc)},
            ) from exc

    return wrapper
