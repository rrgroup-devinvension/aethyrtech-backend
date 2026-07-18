import time
import logging
from celery import shared_task
from experience_cloud.executions.models import DataDumpTask
from experience_cloud.executions.services import ExecutionManager

logger = logging.getLogger(__name__)

# Mock function to call a 3rd party API
def call_third_party_api(location_id):
    logger.info(f"Calling third party API for location {location_id}...")
    time.sleep(60) # Mock API call latency
    return {"status": "success", "data": "Mock data from API"}

@shared_task(name='experience_cloud.market_data.tasks.process_location_dump', rate_limit='100/m')
def process_location_dump(execution_id, task_id, location_id):
    logger.info(f"Starting process_location_dump for Execution: {execution_id}, Task: {task_id}, Location: {location_id}")
    
    # Mark task as running
    ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'RUNNING')
    
    try:
        # Perform the actual API call
        result = call_third_party_api(location_id)
        
        # Update success and trigger finalize check
        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'SUCCESS')
        
    except Exception as e:
        logger.error(f"Task {task_id} failed for location {location_id}: {e}")
        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=str(e))
