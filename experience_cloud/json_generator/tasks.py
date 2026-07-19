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

import json
import os
import uuid
from django.conf import settings
from django.utils import timezone

# Mock function to build and save the actual file
def build_and_save_file(template_name, shared_ram_data, brand_name, region_name):
    logger.info(f"Building JSON for template {template_name} using shared data")
    time.sleep(2) # Mock some processing time (reduced from 15s so testing is faster)
    
    # Generate mock JSON content
    data = {
        "template": template_name,
        "region_data": shared_ram_data,
        "timestamp": time.time(),
        "mock_items": [{"id": i, "value": f"item {i}"} for i in range(10)]
    }
    
    # Save to dynamic media folders based on brand and region
    import shutil
    
    brand_folder = str(brand_name).strip().replace(' ', '_').lower()
    region_folder = str(region_name).strip().replace(' ', '_').lower()
    safe_template = str(template_name).strip().replace(' ', '_').lower()
    
    active_dir = os.path.join(settings.MEDIA_ROOT, 'brands', brand_folder, region_folder)
    os.makedirs(active_dir, exist_ok=True)
    
    file_name = f"{safe_template}.json"
    file_path = os.path.join(active_dir, file_name)
    
    # Archive logic: if old file exists, move it
    if os.path.exists(file_path):
        archive_date = timezone.now().strftime('%Y-%m-%d')
        archive_timestamp = timezone.now().strftime('%H%M%S')
        archive_dir = os.path.join(settings.MEDIA_ROOT, 'archive', brand_folder, region_folder, archive_date)
        os.makedirs(archive_dir, exist_ok=True)
        
        archive_file_name = f"{safe_template}_{archive_timestamp}.json"
        archive_file_path = os.path.join(archive_dir, archive_file_name)
        shutil.move(file_path, archive_file_path)
    
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)
        
    file_size = os.path.getsize(file_path)
    
    return {
        "file_name": file_name,
        "file_path": file_path,
        "file_size": file_size,
        "checksum": str(uuid.uuid4()) # Mock checksum
    }

@shared_task(name='experience_cloud.json_generator.tasks.process_region_batch')
def process_region_batch(execution_id, region_id, file_task_ids):
    logger.info(f"Starting process_region_batch for Execution: {execution_id}, Region: {region_id}")
    
    from experience_cloud.json_generator.models import RegionJsonFile
    
    try:
        # Fetch the Region to get Brand and Region names
        region_obj = RegionJsonFile.objects.filter(region_id=region_id).first().region
        brand_name = region_obj.brand.name if region_obj and region_obj.brand else 'UnknownBrand'
        region_name = region_obj.name if region_obj else 'UnknownRegion'

        # 1. Calculate the heavy shared RAM data exactly once for this region
        shared_ram_data = calculate_region_data(region_id)
        
        # 2. Iterate through the files (tasks)
        for task_id in file_task_ids:
            # State validation: Abort if the task was manually stopped or updated before execution began
            region_file = RegionJsonFile.objects.filter(task_id=str(task_id)).first()
            if region_file and region_file.status not in ['PENDING', 'RUNNING']:
                logger.warning(f"Task {task_id} aborted due to manual state change (current status: {region_file.status})")
                continue
                
            # Mark as running
            ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'RUNNING')
            
            try:
                # Fetch task to know which template to build
                task = JsonFileTask.objects.get(id=task_id)
                template_name = task.metadata.get('template') if task.metadata else 'Unknown'
                
                # Use the shared data to build the file
                start_time = time.time()
                file_info = build_and_save_file(template_name, shared_ram_data, brand_name, region_name)
                duration = time.time() - start_time
                
                # Mark Success (This also triggers the atomic check to finish the execution)
                ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'SUCCESS')
                
                # Update RegionJsonFile
                if task.metadata and 'file_id' in task.metadata:
                    RegionJsonFile.objects.filter(id=task.metadata['file_id']).update(
                        file_name=file_info['file_name'],
                        file_path=file_info['file_path'],
                        file_size=file_info['file_size'],
                        checksum=file_info['checksum'],
                        generation_duration=duration,
                        status='SUCCESS',
                        last_generated_at=timezone.now()
                    )
                
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'FAILED', error=str(e))
                if task.metadata and 'file_id' in task.metadata:
                    RegionJsonFile.objects.filter(id=task.metadata['file_id']).update(
                        status='FAILED',
                        error_message=str(e)
                    )
                
    except Exception as e:
        logger.error(f"Region batch {region_id} failed completely: {e}")
        # If the batch setup fails, fail all child tasks
        for task_id in file_task_ids:
            ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'FAILED', error="Batch initialization failed: " + str(e))
