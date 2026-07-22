from experience_cloud.json_generator.utils import ItemGenerator
import time
import logging
from celery import shared_task
from experience_cloud.executions.models import JsonFileTask
from experience_cloud.executions.services import ExecutionManager
from experience_cloud.json_generator.models import RegionJsonFile
from experience_cloud.json_generator.collectors import get_all_products
from experience_cloud.json_generator.builders import get_builder_for_template
from core.organizations.models import Region
from django.utils import timezone
from experience_cloud.json_generator.schemas import RegionDataSchema

logger = logging.getLogger(__name__)

def get_region_data(region_id: int) -> RegionDataSchema:
    logger.info(f"Loading heavy data for region {region_id} into RAM...")
    from core.organizations.models import Region, Competitor
    from experience_cloud.catalog.models import Keyword, Location
    from experience_cloud.json_generator.schemas import RegionDataSchema
    
    region = Region.objects.select_related('brand__category').get(id=region_id)
    brand = region.brand
    
    brand_id = brand.id if brand else 0
    brand_name = brand.name if brand else ''
    region_name = region.name
    category_id = brand.category_id if brand else None
    
    brands = [brand_name] if brand_name else []
    for comp in Competitor.objects.filter(region_id=region_id):
        brands.append(comp.name)
        
    keywords_qs = Keyword.objects.filter(
        region_id=region_id, 
        category_id=category_id
    ).select_related('platform__api_provider')
    
    keywords: dict = {}
    platforms_map: dict = {}
    distinct_keywords_map: dict = {}
    
    for kw in keywords_qs:
        plat = kw.platform
        plat_val = plat.value if plat else 'all'
        
        if plat_val not in keywords:
            keywords[plat_val] = []
        keywords[plat_val].append(kw.keyword)
        
        if plat and plat.id not in platforms_map:
            api_prov = plat.api_provider
            platforms_map[plat.id] = {
                "platform_name": plat.name,
                "platform_id": plat.id,
                "api_provider_name": api_prov.name if api_prov else "",
                "api_provider_code": api_prov.code if api_prov else "",
                "api_provider_id": api_prov.id if api_prov else 0,
                "keywords": [],
                "locations": []
            }
            
        kw_item = {"id": kw.id, "name": kw.keyword}
        if plat:
            platforms_map[plat.id]["keywords"].append(kw_item)
            
        if kw.keyword not in distinct_keywords_map:
            distinct_keywords_map[kw.keyword] = kw_item
            
    pincodes_qs = Location.objects.filter(
        region_id=region_id, 
        category_id=category_id
    ).select_related('platform__api_provider')
    
    pincodes: dict = {}
    distinct_locations_map: dict = {}
    display_locations_set: set = set()
    display_locations: list = []
    
    for loc in pincodes_qs:
        plat = loc.platform
        plat_val = plat.value if plat else 'all'
        pin_val = loc.pincode or loc.address
        
        if pin_val:
            if plat_val not in pincodes:
                pincodes[plat_val] = []
            pincodes[plat_val].append(pin_val)
            
        if plat and plat.id not in platforms_map:
            api_prov = plat.api_provider
            platforms_map[plat.id] = {
                "platform_name": plat.name,
                "platform_id": plat.id,
                "api_provider_name": api_prov.name if api_prov else "",
                "api_provider_code": api_prov.code if api_prov else "",
                "api_provider_id": api_prov.id if api_prov else 0,
                "keywords": [],
                "locations": []
            }
            
        loc_item = {
            "pincode": loc.pincode,
            "location": loc.address,
            "lat": float(loc.lat) if loc.lat is not None else None,
            "lng": float(loc.lng) if loc.lng is not None else None
        }
        
        if plat:
            platforms_map[plat.id]["locations"].append(loc_item)
            
        loc_key = f"{loc.pincode}_{loc.address}"
        if loc_key not in distinct_locations_map:
            distinct_locations_map[loc_key] = loc_item
            
        disp_val = loc.pincode if loc.pincode else loc.address
        if disp_val and disp_val not in display_locations_set:
            display_locations_set.add(disp_val)
            display_locations.append(disp_val)
    
    result: RegionDataSchema = {
        "brand_name": brand_name,
        "brand_id": brand_id,
        "region_name": region_name,
        "region_id": region_id,
        "brands": brands,
        "platforms": list(platforms_map.values()),
        "keywords": list(distinct_keywords_map.values()),
        "locations": list(distinct_locations_map.values()),
        "display_locations": display_locations,
        "display_keywords": [kw["name"] for kw in distinct_keywords_map.values()],
        "display_platforms": [plat["platform_name"] for plat in platforms_map.values()]
    }
    
    return result


@shared_task(name='experience_cloud.json_generator.tasks.process_region_batch')
def process_region_batch(execution_id: int, region_id: int, file_task_ids: list) -> None:
    logger.info(f"Starting process_region_batch for Execution: {execution_id}, Region: {region_id}")
    
    try:
        region_data: RegionDataSchema = get_region_data(region_id)
        product_generator: ItemGenerator = get_all_products(region_data)
        
        for task_id in file_task_ids:
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
                
                builder_func = get_builder_for_template(template_name)
                
                start_time = time.time()
                is_file_saved, json_payload = builder_func(
                    region_data=region_data,
                    task=task,
                    products=product_generator,
                    template=template_name
                )
                
                brand_name = region_data.get("brand_name", "unknown")
                
                if not is_file_saved:
                    # Orchestrator saves the file
                    from experience_cloud.json_generator.utils import save_json_to_file
                    file_name, file_path = save_json_to_file(json_payload, brand_name, template_name)
                else:
                    # Builder already handled saving (including extra files, DB updates, etc)
                    # We extract the file_name and file_path from the payload
                    file_name = json_payload.get("file_name") if isinstance(json_payload, dict) else None
                    file_path = json_payload.get("file_path") if isinstance(json_payload, dict) else None
                
                duration = time.time() - start_time
                
                # Mark Success (This also triggers the atomic check to finish the execution)
                ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'SUCCESS')
                
                # Update RegionJsonFile (if orchestrator saved the file)
                if task.metadata and 'file_id' in task.metadata:
                    update_kwargs = {
                        "generation_duration": duration,
                        "status": 'SUCCESS',
                        "last_generated_at": timezone.now()
                    }
                    
                    if not is_file_saved and file_name and file_path:
                        import os
                        from django.conf import settings
                        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
                        file_size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                        
                        update_kwargs.update({
                            "file_name": file_name,
                            "file_path": file_path,
                            "file_size": file_size,
                            "checksum": "calculated",
                        })
                        
                    RegionJsonFile.objects.filter(id=task.metadata['file_id']).update(**update_kwargs)
                
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
