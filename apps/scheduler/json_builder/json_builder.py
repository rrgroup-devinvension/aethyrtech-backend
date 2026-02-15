import logging
from django.utils import timezone
from apps.scheduler.json_builder.brand_dashboard import brand_dashboard_data_builder
from apps.scheduler.json_builder.category_view import category_view_data_builder
from apps.scheduler.json_builder.brand_audit import brand_audit_data_builder
from apps.scheduler.json_builder.keyword_matrix import keyword_matrix_builder
from apps.scheduler.json_builder.catalog import catalog_data_builder
from apps.scheduler.json_builder.reports import reports_data_builder
from apps.scheduler.json_builder.content_insights import content_insights_data_builder
from apps.scheduler.json_builder.keyword_counts import keyword_counts_builder
from apps.scheduler.json_builder.services.data_collector import get_all_products
from apps.scheduler.json_builder.cartesian_products_pincodes import cartesian_products_pincodes_builder
from apps.scheduler.enums import JsonTemplate
from apps.scheduler.exceptions import SchedulerBaseException, DataProcessingException
from apps.scheduler.utility.tasks_utility import get_brands, get_brand_platform_keywords
from apps.scheduler.models import BrandJsonFile
from apps.scheduler.utility.jsonbuilder_api_logger import log_start, log_success, log_error

logger = logging.getLogger(__name__)

def build_json(brands, keywords, products, task, brand_id, brand_name, template, platform_type):
    if template == JsonTemplate.BRAND_DASHBOARD.slug:
        return brand_dashboard_data_builder(task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.CATEGORY_VIEW.slug:
        return category_view_data_builder(brands, keywords, products, task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.BRAND_AUDIT.slug:
        return brand_audit_data_builder(brands, keywords, products, task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.CATALOG.slug:
        return catalog_data_builder(brands, keywords, products, task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.REPORTS.slug:
        return reports_data_builder(task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.CONTENT_INSIGHTS.slug:
        return content_insights_data_builder(task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.KEYWORD_MATRIX.slug:
        return keyword_matrix_builder(brands, keywords, products, task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.KEYWORD_COUNTS.slug:
        return keyword_counts_builder(brands, keywords, products, task, brand_id, brand_name, template, platform_type)
    elif template == JsonTemplate.CARTESIAN_PRODUCTS_PINCODES.slug:
        return cartesian_products_pincodes_builder(brands, keywords, products, task, brand_id, brand_name, template, platform_type)
    else:
        raise DataProcessingException(message=f"Unsupported JSON template: {template}")

def perform_json_build(task):
    t_id = getattr(task, 'id', 'unknown')
    logger.info(f"JSON_BUILD STARTED | Task={t_id}")
    log_start(task_id=t_id, info={'entity': getattr(task, 'entity_id', None)})
    ctx = task.extra_context or {}
    brand_id = ctx.get("brand_id") or task.entity_id
    brand_name = ctx.get("brand_name") or "Unknown Brand"
    platform_type = ctx.get("platform_type")
    templates = ctx.get("templates") or [t.slug for t in JsonTemplate]
    failures = []
    brands = get_brands(brand_id)
    brand_keywords = get_brand_platform_keywords()
    keywords = brand_keywords.get(brand_name) or {}
    products = get_all_products(platform_type, keywords, brands[:1])
    for template in templates:
        json_file = None
        try:
            json_file, _ = BrandJsonFile.objects.get_or_create(brand_id=brand_id,template=template)
            json_file.last_run_time = timezone.now()
            json_file.last_run_status = "RUNNING"
            json_file.error_message = None
            json_file.save(update_fields=["last_run_time","last_run_status","error_message"])
            filename, file_path = build_json(brands, keywords, products, task,brand_id,brand_name,template,platform_type)
            json_file.filename = filename
            json_file.file_path = file_path
            json_file.last_completed_time = timezone.now()
            json_file.last_run_status = "SUCCESS"
            json_file.last_synced = timezone.now()
            json_file.error_message = None
            json_file.save(update_fields=["filename","file_path","last_completed_time","last_run_status","last_synced","error_message"])

        except SchedulerBaseException as exc:
            failures.append({"template": template,"code": exc.error_code,"message": exc.user_message})
            logger.error(f"JSON_BUILD FAILED → Brand={brand_id} Template={template} Error={exc.user_message}")

            if json_file:
                log_error(task_id=t_id, error=exc.user_message, extra={'template': template})
                json_file.last_run_status = "FAILED"
                json_file.last_completed_time = timezone.now()
                json_file.last_synced = timezone.now()
                json_file.error_message = exc.user_message
                json_file.save(update_fields=["last_run_status","last_completed_time","last_synced","error_message"])

        except Exception as exc:
            failures.append({"template": template,"code": "SYSTEM_ERROR","message": str(exc)})
            logger.exception(f"JSON_BUILD CRASHED → Brand={brand_id} Template={template}")
            if json_file:
                log_error(task_id=t_id, error=str(exc), extra={'template': template})
                json_file.last_run_status = "FAILED"
                json_file.last_completed_time = timezone.now()
                json_file.last_synced = timezone.now()
                json_file.error_message = str(exc)
                json_file.save(update_fields=["last_run_status","last_completed_time","last_synced","error_message"])

    if failures:
        combined_message = ", ".join([f"{f['template']}: {f['message']}" for f in failures])
        logger.error("JSON_BUILD FAILURES → %s", combined_message)
        log_error(task_id=t_id, error='JSON_BUILD failures', extra={'failures': failures})
        raise DataProcessingException(message=combined_message,extra=failures)
    logger.info(f"JSON_BUILD COMPLETED | Task={t_id}")
    log_success(task_id=t_id, info={'templates': templates})
