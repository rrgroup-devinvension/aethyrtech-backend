from experience_cloud.market_data.schemas import DataDumpResponseSchema
from experience_cloud.market_data.services.dispatcher import DataDumpDispatcher
from experience_cloud.market_data.schemas import DataDumpSchema
import time
import logging
import traceback
from django.utils import timezone
from celery import shared_task
from django.db import transaction

from experience_cloud.executions.models import DataDumpTask
from experience_cloud.executions.services import ExecutionManager
from experience_cloud.catalog.models import Keyword, Location
from experience_cloud.market_data.models import ApiDump
from experience_cloud.market_integrations.models.xbytes import XBytesProduct
from experience_cloud.market_integrations.clients.xbyte_client import XByteClient

logger = logging.getLogger(__name__)


def build_data_dump_schema(keyword_id: int, location_id: int) -> DataDumpSchema:
    """
    Given a keyword and location ID, fetches the corresponding objects
    and constructs a standardized DataDumpSchema for the API services.
    """
    # 1. Fetch DB objects and their relations in one hit
    # Assuming the relation name from Platform to ApiProvider is 'api_provider'
    keyword_obj = Keyword.objects.select_related('platform__api_provider', 'region__brand', 'category').get(id=keyword_id)
    location_obj = Location.objects.get(id=location_id)
    
    platform_obj = keyword_obj.platform
    brand_obj = keyword_obj.region.brand if keyword_obj.region else None
    category_obj = keyword_obj.category
    provider_obj = platform_obj.api_provider if platform_obj else None
    
    # 2. Format the physical location constraint
    location_str = str(location_obj.pincode) if location_obj.pincode else str(location_obj.address)
    
    # 3. Construct the exact schema dictionary
    schema = DataDumpSchema(
        # Location mapping
        display_location=location_str,
        location_id=location_obj.id,
        
        # Platform mapping
        platform_name=platform_obj.name if platform_obj else 'Unknown',
        platform_id=platform_obj.id if platform_obj else None,
        platform_code=platform_obj.code if platform_obj else 'Unknown',
        
        # Keyword mapping
        keyword_name=keyword_obj.keyword,
        keyword_id=keyword_obj.id,
        
        # Category mapping
        category_name=category_obj.name if category_obj else None,
        category_id=category_obj.id if category_obj else None,
        
        # Brand mapping
        brand_name=brand_obj.name if brand_obj else None,
        brand_id=brand_obj.id if brand_obj else None,
        
        # Provider mapping (Dynamically pulled from Platform's Foreign Key!)
        provider_name=provider_obj.name if provider_obj else 'Unknown',
        provider_code=provider_obj.code if provider_obj else 'UNKNOWN',
        provider_id=provider_obj.id if provider_obj else None,
        configuration=platform_obj.configuration if platform_obj else {}
    )
    
    return schema

@shared_task(name='experience_cloud.market_data.tasks.process_location_dump', rate_limit='100/m')
def process_location_dump(execution_id, task_id, keyword_id, location_id):
    logger.info(f"Starting process_location_dump for Execution: {execution_id}, Task: {task_id}, Keyword: {keyword_id}, Location: {location_id}")
    
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
        
        # 1. Use the new helper method to build the exact Schema dictionary dynamically!
        schema = build_data_dump_schema(keyword_id=keyword_id, location_id=location_id)
        
        # 2. Pass the Schema to Dispatcher instead of hardcoded XByte logic!
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
            raise Exception(response.get("message", "Unknown Service Error"))
            
    except Exception as e:
        full_trace = traceback.format_exc()
        logger.error(f"Data Dump Task {task_id} failed: {e}\n{full_trace}")
        
        ApiDump.objects.filter(task_id=str(task_id)).update(
            status='FAILED',
            error_message=full_trace
        )
        
        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=full_trace)
