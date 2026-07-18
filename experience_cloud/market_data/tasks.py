import time
import logging
from celery import shared_task
from experience_cloud.executions.models import DataDumpTask
from experience_cloud.executions.services import ExecutionManager

from experience_cloud.market_data.models import ApiDump

logger = logging.getLogger(__name__)

# Mock function to call a 3rd party API
def call_third_party_api(location_id):
    logger.info(f"Calling third party API for location {location_id}...")
    time.sleep(2) # Mock API call latency (reduced for testing)
    return {"status": "success", "items_found": 12}

@shared_task(name='experience_cloud.market_data.tasks.process_location_dump', rate_limit='100/m')
def process_location_dump(execution_id, task_id, location_id):
    logger.info(f"Starting process_location_dump for Execution: {execution_id}, Task: {task_id}, Location: {location_id}")
    
    # Mark task as running
    ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'RUNNING')
    
    try:
        start_time = time.time()
        # Perform the actual API call
        response = call_third_party_api(location_id)
        duration = time.time() - start_time
        
        # Update success and trigger finalize
        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'SUCCESS')
        
        # Update ApiDump
        ApiDump.objects.filter(task_id=str(task_id)).update(
            products_found=response['items_found'],
            response_time=duration,
            status='SUCCESS',
            error_message=None
        )
        
    except Exception as e:
        logger.error(f"Data Dump Task {task_id} failed: {e}")
        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=str(e))
        ApiDump.objects.filter(task_id=str(task_id)).update(
            status='FAILED',
            error_message=str(e)
        )
