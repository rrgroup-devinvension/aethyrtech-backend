import logging
import time
import traceback

from celery import shared_task

from experience_cloud.executions.models import DataDumpTask
from experience_cloud.executions.services import ExecutionManager
from experience_cloud.market_data.models import ApiDump
from experience_cloud.market_data.schemas import DataDumpSchema
from experience_cloud.market_data.services.dispatcher import DataDumpDispatcher

logger = logging.getLogger(__name__)


def build_data_dump_schema(metadata: dict, platform_obj, category_obj, provider_obj) -> DataDumpSchema:
    """Constructs a standardized DataDumpSchema for the API services from task metadata."""
    schema = DataDumpSchema(
        # Location mapping
        display_location=metadata.get('location_name', ''),

        # Platform mapping
        platform_name=platform_obj.name,
        platform_id=platform_obj.id,
        platform_code=platform_obj.code,

        # Keyword mapping
        keyword_name=metadata.get('keyword_name', ''),

        # Category mapping
        category_name=getattr(category_obj, "name", None) if category_obj else None,
        category_id=getattr(category_obj, "id", None) if category_obj else None,

        # Regional mapping (list of regions for cost splitting)
        regions=metadata.get('regions', []),

        # API Provider mapping
        provider_name=provider_obj.name if provider_obj else '',
        provider_code=provider_obj.code if provider_obj else '',
        provider_id=provider_obj.id if provider_obj else None,
        configuration=platform_obj.configuration if platform_obj else {},
    )

    return schema


@shared_task(name='experience_cloud.market_data.tasks.process_location_dump', rate_limit='100/m')
def process_location_dump(execution_id: int, task_id: int, keyword_name: str, location_name: str):
    """Distributed worker task that processes a single keyword-location combination."""
    logger.info(
        f"Starting process_location_dump for Execution: {execution_id}, "
        f"Task: {task_id}, Keyword: {keyword_name}, Location: {location_name}"
    )

    # State validation: Abort if the task was manually stopped or updated before execution began
    api_dump = ApiDump.objects.filter(task_id=str(task_id)).first()
    if api_dump and api_dump.status not in ['PENDING', 'RUNNING']:
        logger.warning(f"Task {task_id} aborted due to manual state change (current status: {api_dump.status})")
        return

    # Mark task as running
    ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'RUNNING')

    # Mark ApiDump as running
    ApiDump.objects.filter(task_id=str(task_id)).update(status='RUNNING')

    try:
        start_time = time.time()

        # 1. Fetch metadata and objects for schema building
        try:
            task = DataDumpTask.objects.select_related('execution').get(id=task_id)
        except DataDumpTask.DoesNotExist:
            logger.warning(f"DataDumpTask {task_id} missing. Ignoring task execution.")
            return

        metadata = task.metadata

        from core.categories.models import Category
        from experience_cloud.catalog.models import Platform

        # We need Platform and API Provider
        api_dump = ApiDump.objects.get(task_id=str(task_id))
        platform_obj = (
            Platform.objects.select_related('api_provider').get(id=api_dump.platform_id)
            if api_dump.platform_id else None
        )
        provider_obj = getattr(platform_obj, "api_provider", None) if platform_obj else None

        category_obj = None
        if api_dump.category_id:
            category_obj = Category.objects.filter(id=api_dump.category_id).first()

        # 2. Use the new helper method to build the exact Schema dictionary dynamically!
        schema = build_data_dump_schema(metadata, platform_obj, category_obj, provider_obj)

        # 3. Pass the Schema to Dispatcher instead of hardcoded XByte logic!
        dispatcher = DataDumpDispatcher()
        response = dispatcher.execute(schema)

        duration = time.time() - start_time

        # 3. Handle Response strictly based on the defined DataDumpResponseSchema
        if response.get("status") == "success":
            items_count = response.get("items_count", 0)

            # IMPORTANT: Update ApiDump BEFORE updating ExecutionManager
            ApiDump.objects.filter(task_id=str(task_id)).update(
                products_found=items_count,
                product_count=items_count,
                response_time=duration,
                status='SUCCESS',
                error_message=None
            )

            # Update success and trigger finalize
            ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'SUCCESS')
        else:
            # API returned a logical error (e.g. Location Not Found)
            # We don't want a python traceback in the DB for this, just the raw server response
            error_msg = response.get("message", "Unknown Service Error")
            
            logger.warning(f"Data Dump Task {task_id} failed with logical error: {error_msg}")
            
            ApiDump.objects.filter(task_id=str(task_id)).update(
                status='FAILED',
                error_message=str(error_msg)
            )
            ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=str(error_msg))
            return  # Finish gracefully so we don't hit the generic Exception handler

    except Exception as e:
        full_trace = traceback.format_exc()
        logger.exception(f"Data Dump Task {task_id} failed: {e}")

        ApiDump.objects.filter(task_id=str(task_id)).update(
            status='FAILED',
            error_message=full_trace
        )

        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=full_trace)
