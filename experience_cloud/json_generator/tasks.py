import time
import logging
from celery import shared_task
from experience_cloud.executions.models import JsonFileTask
from experience_cloud.executions.services import ExecutionManager

logger = logging.getLogger(__name__)

# Mock function to load heavy region data exactly once
def calculate_region_data(region_id):
    logger.info(f"Loading heavy data for region {region_id} into RAM...")
    time.sleep(90) # Mock heavy DB query
    return {"region_id": region_id, "mock_data": "Heavy payload loaded"}

# Mock function to build and save the actual file
def build_and_save_file(template_name, shared_ram_data):
    logger.info(f"Building JSON for template {template_name} using shared data")
    time.sleep(15) # Mock file building and saving

@shared_task(name='experience_cloud.json_generator.tasks.process_region_batch')
def process_region_batch(execution_id, region_id, file_task_ids):
    logger.info(f"Starting process_region_batch for Execution: {execution_id}, Region: {region_id}")
    
    try:
        # 1. Calculate the heavy shared RAM data exactly once for this region
        shared_ram_data = calculate_region_data(region_id)
        
        # 2. Iterate through the files (tasks)
        for task_id in file_task_ids:
            # Mark as running
            ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'RUNNING')
            
            try:
                # Fetch task to know which template to build
                task = JsonFileTask.objects.get(id=task_id)
                template_name = task.metadata.get('template') if task.metadata else 'Unknown'
                
                # Use the shared data to build the file
                build_and_save_file(template_name, shared_ram_data)
                
                # Mark Success (This also triggers the atomic check to finish the execution)
                ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'SUCCESS')
                
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'FAILED', error=str(e))
                
    except Exception as e:
        logger.error(f"Region batch {region_id} failed completely: {e}")
        # If the batch setup fails, fail all child tasks
        for task_id in file_task_ids:
            ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'FAILED', error="Batch initialization failed: " + str(e))
