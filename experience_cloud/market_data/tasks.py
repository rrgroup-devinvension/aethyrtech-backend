import time
import logging
from django.utils import timezone
from celery import shared_task
from experience_cloud.executions.models import DataDumpTask
from experience_cloud.executions.services import ExecutionManager
from experience_cloud.catalog.models import Keyword, Location
from experience_cloud.market_data.models import ApiDump, Product

logger = logging.getLogger(__name__)

# Mock function to call a 3rd party API and generate products
def call_third_party_api(keyword_obj, location_obj):
    logger.info(f"Calling third party API for location {location_obj.id}...")
    time.sleep(2) # Mock API call latency (reduced for testing)
    
    items_found = 12
    run_date = timezone.now().strftime('%Y-%m-%d')
    location_str = str(location_obj.pincode) if location_obj.pincode else str(location_obj.address)
    platform_name = keyword_obj.platform.name if keyword_obj.platform else 'Unknown'
    
    combined_name = f"{keyword_obj.keyword}"
    
    # Archive/Clear old products for this keyword and location to avoid endless duplicates
    Product.objects.filter(
        platform=platform_name,
        keyword=combined_name,
        location=location_str
    ).delete()
    
    mock_products = []
    for i in range(items_found):
        mock_products.append(
            Product(
                platform=platform_name,
                keyword=combined_name,
                location=location_str,
                title=f"Mock Product {i+1} for {combined_name}",
                brand="MockBrand",
                rank=i+1,
                availability="In Stock",
                mrp="999.00",
                sell_price="799.00",
                run_date=run_date
            )
        )
    Product.objects.bulk_create(mock_products)
    
    return {"status": "success", "items_found": items_found}

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
        
        keyword_obj = Keyword.objects.get(id=keyword_id)
        location_obj = Location.objects.get(id=location_id)
        
        # Perform the actual API call and save products
        response = call_third_party_api(keyword_obj, location_obj)
        duration = time.time() - start_time
        
        # IMPORTANT: Update ApiDump BEFORE updating ExecutionManager
        # because ExecutionManager might finalize and delete the active task!
        ApiDump.objects.filter(task_id=str(task_id)).update(
            products_found=response['items_found'],
            product_count=response['items_found'],
            response_time=duration,
            status='SUCCESS',
            error_message=None
        )
        
        # Update success and trigger finalize
        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'SUCCESS')
        
    except Exception as e:
        logger.error(f"Data Dump Task {task_id} failed: {e}")
        
        ApiDump.objects.filter(task_id=str(task_id)).update(
            status='FAILED',
            error_message=str(e)
        )
        
        ExecutionManager.update_task_status(DataDumpTask, task_id, execution_id, 'FAILED', error=str(e))
