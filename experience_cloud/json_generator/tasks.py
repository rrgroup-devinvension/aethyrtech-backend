import logging
import time

from celery import shared_task
from django.utils import timezone

from experience_cloud.executions.models import JsonFileTask
from experience_cloud.executions.services import ExecutionManager
from experience_cloud.json_generator.builders import get_builder_for_template
from experience_cloud.json_generator.collectors import get_all_products
from experience_cloud.json_generator.models import RegionJsonFile
from experience_cloud.json_generator.schemas import RegionDataSchema
from experience_cloud.json_generator.utils import ItemGenerator

logger = logging.getLogger(__name__)

def get_region_data(region_id: int) -> RegionDataSchema:
    """Extract and aggregate cross-platform catalog data into a RegionDataSchema dictionary."""
    logger.info(f"Loading heavy data for region {region_id} into RAM...")
    from core.organizations.models import Competitor, Region
    from experience_cloud.catalog.models import Keyword, Location
    from experience_cloud.json_generator.schemas import RegionDataSchema

    region = Region.objects.select_related('brand__category').get(id=region_id)
    brand = region.brand

    brand_id = brand.id
    brand_name = brand.name
    region_name = region.name
    category_id = brand.category.id if hasattr(brand, 'category') and brand.category else None

    brands: dict = {}
    if brand_name:
        aliases_str = brand.aliases if brand.aliases else ""
        aliases = [a.strip() for a in aliases_str.split(',') if a.strip()] if aliases_str else []
        brands[brand_name] = aliases

    for comp in Competitor.objects.filter(region_id=region_id):
        aliases_str = comp.aliases if comp.aliases else ""
        aliases = [a.strip() for a in aliases_str.split(',') if a.strip()] if aliases_str else []
        brands[comp.name] = aliases

    keywords_qs = Keyword.objects.filter(
        region_id=region_id,
        category_id=category_id
    ).select_related('platform__api_provider').order_by('display_order')

    keywords: dict = {}
    platforms_map: dict = {}
    distinct_keywords_map: dict = {}

    for kw in keywords_qs:
        plat = kw.platform
        plat_val = plat.code if plat.code else 'all'

        if plat_val not in keywords:
            keywords[plat_val] = []
        keywords[plat_val].append(kw.keyword)

        if plat.id not in platforms_map:
            api_prov = plat.api_provider
            platforms_map[plat.id] = {
                "platform_name": plat.name,
                "platform_id": plat.id,
                "platform_code": plat.code if plat.code else "",
                "api_provider_name": api_prov.name if api_prov else "",
                "api_provider_code": api_prov.code if api_prov else "",
                "api_provider_id": api_prov.id if api_prov else 0,
                "keywords": [],
                "locations": []
            }

        kw_item = {"id": kw.id, "name": kw.keyword}
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
        plat_val = plat.code if plat.code else 'all'
        pin_val = loc.pincode or loc.address

        if pin_val:
            if plat_val not in pincodes:
                pincodes[plat_val] = []
            pincodes[plat_val].append(pin_val)

        if plat.id not in platforms_map:
            api_prov = plat.api_provider
            platforms_map[plat.id] = {
                "platform_name": plat.name,
                "platform_id": plat.id,
                "platform_code": plat.code if plat.code else "",
                "api_provider_name": api_prov.name if api_prov else "",
                "api_provider_code": api_prov.code if api_prov else "",
                "api_provider_id": api_prov.id if api_prov else 0,
                "keywords": [],
                "locations": []
            }

        loc_item = {
            "id": loc.id,
            "pincode": loc.pincode,
            "location": loc.address,
            "lat": float(loc.lat) if loc.lat is not None else None,
            "lng": float(loc.lng) if loc.lng is not None else None
        }

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
        "display_brands": list(brands.keys()),
        "platforms": { plat["platform_code"]: plat for plat in platforms_map.values() if plat["platform_code"] },
        "keywords": list(distinct_keywords_map.values()),
        "locations": list(distinct_locations_map.values()),
        "display_locations": display_locations,
        "display_keywords": [kw["name"] for kw in distinct_keywords_map.values()],
        "display_platforms": [plat["platform_name"] for plat in platforms_map.values()]
    }

    return result


@shared_task(name='experience_cloud.json_generator.tasks.process_region_batch')
def process_region_batch(execution_id: int, region_id: int, file_task_ids: list) -> None:
    """Orchestrate Celery worker execution of JSON file builders for a batch of templates tied to a specific region."""
    ctx = f"[JSON Gen | Exec: {execution_id} | Region: {region_id}]"
    logger.info(f"{ctx} Starting process_region_batch for {len(file_task_ids)} files")

    try:
        region_data: RegionDataSchema = get_region_data(region_id)

        ctx = (
            f"[JSON Gen | Exec: {execution_id} | Region: {region_data.get('region_name', region_id)} "
            f"| Brand: {region_data.get('brand_name', 'Unknown')}]"
        )
        from experience_cloud.json_generator.models import ProcessTypeCodes

        has_automatic = RegionJsonFile.objects.filter(
            task_id__in=[str(t) for t in file_task_ids],
            template__process_type=ProcessTypeCodes.AUTOMATIC.value
        ).exists()

        if has_automatic:
            logger.info(f"{ctx} Region data loaded. Fetching all products for automatic templates...")
            product_generator: ItemGenerator | None = get_all_products(region_data)
        else:
            logger.info(f"{ctx} All templates are manual. Skipping product fetch.")
            product_generator = None

        for task_id in file_task_ids:
            region_file = RegionJsonFile.objects.select_related('template').filter(task_id=str(task_id)).first()
            if region_file and region_file.status not in ['PENDING', 'RUNNING']:
                logger.warning(
                    f"{ctx} Task {task_id} aborted due to manual state change "
                    f"(current status: {region_file.status})"
                )
                continue

            # Mark as running
            ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'RUNNING')

            try:
                # Fetch task to know which template to build
                task = JsonFileTask.objects.get(id=task_id)
                template_name = region_file.template.template if region_file and region_file.template else 'Unknown'

                builder_func = get_builder_for_template(template_name)

                logger.info(f"{ctx} Initiating generation for template: {template_name}")
                start_time = time.time()
                is_file_saved, json_payload = builder_func(
                    region_data=region_data,
                    task=task,
                    products=product_generator,
                    template=template_name
                )

                brand_name = region_data.get("brand_name", "unknown")
                region_name = region_data.get("region_name", "unknown")
                existing_path = region_file.file_path if region_file else None

                if not is_file_saved:
                    # Orchestrator saves the file
                    from experience_cloud.json_generator.utils import save_region_template
                    file_name, file_path = save_region_template(
                        json_payload, brand_name, template_name, region_name, existing_path=existing_path
                    )
                else:
                    # Builder already handled saving (including extra files, DB updates, etc)
                    # We extract the file_name and file_path from the payload
                    file_name = json_payload.get("file_name") if isinstance(json_payload, dict) else None
                    file_path = json_payload.get("file_path") if isinstance(json_payload, dict) else None

                duration = time.time() - start_time
                logger.info(f"{ctx} Successfully finished template: {template_name} in {duration:.2f}s")

                # Mark Success (This also triggers the atomic check to finish the execution)
                ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'SUCCESS')

                # Update RegionJsonFile (if orchestrator saved the file)
                if task.metadata and 'file_id' in task.metadata:
                    update_kwargs = {
                        "generation_duration": duration,
                        "products_processed": getattr(product_generator, 'total_count', 0),
                        "status": 'SUCCESS',
                        "last_generated_at": timezone.now(),
                        "updated_at": timezone.now()
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

            except Exception as e:  # noqa: BLE001
                logger.error(f"{ctx} Task {task_id} failed: {e}")
                ExecutionManager.update_task_status(JsonFileTask, task_id, execution_id, 'FAILED', error=str(e))
                if task.metadata and 'file_id' in task.metadata:
                    RegionJsonFile.objects.filter(id=task.metadata['file_id']).update(
                        status='FAILED',
                        error_message=str(e),
                        updated_at=timezone.now()
                    )

    except Exception as e:
        logger.exception(f"{ctx} Region batch failed completely")
        # If the batch setup fails, fail all child tasks
        for task_id in file_task_ids:
            ExecutionManager.update_task_status(
                JsonFileTask, task_id, execution_id, 'FAILED', error="Batch initialization failed: " + str(e)
            )

            task_obj = JsonFileTask.objects.filter(id=task_id).first()
            if task_obj and task_obj.metadata and 'file_id' in task_obj.metadata:
                RegionJsonFile.objects.filter(id=task_obj.metadata['file_id']).update(
                    status='FAILED',
                    error_message=f"Batch initialization failed: {e}",
                    updated_at=timezone.now()
                )
    finally:
        if 'product_generator' in locals() and hasattr(product_generator, 'cleanup'):
            product_generator.cleanup()
