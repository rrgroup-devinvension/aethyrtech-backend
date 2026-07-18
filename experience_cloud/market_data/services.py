import logging
from django.utils import timezone
from experience_cloud.executions.models import ActiveExecution, DataDumpTask
from experience_cloud.catalog.models import Keyword, Location

logger = logging.getLogger(__name__)

def trigger_data_dump(scope_type, scope_id, request_user=None):
    """
    Creates an ActiveExecution of type DATA_DUMP and generates
    the corresponding DataDumpTask entries.
    """
    
    # We need to collect combinations of Keyword + Location
    keywords = Keyword.objects.all()
    
    if scope_type == 'CATEGORY':
        keywords = keywords.filter(category_id=scope_id)
        # Find all locations for these categories
        locations = Location.objects.filter(category_id=scope_id)
    
    elif scope_type == 'PLATFORM':
        # the scope_id for PLATFORM might actually need to be a composite of category_id and platform_id 
        # to ensure we don't dump the whole platform across all categories if we only meant one.
        # But for now, assume scope_id is platform_id
        # Wait, let's assume the frontend passes "category_id:platform_id"
        if ':' in str(scope_id):
            cat_id, plat_id = str(scope_id).split(':')
            keywords = keywords.filter(category_id=cat_id, platform_id=plat_id)
            locations = Location.objects.filter(category_id=cat_id, platform_id=plat_id)
        else:
            keywords = keywords.filter(platform_id=scope_id)
            locations = Location.objects.filter(platform_id=scope_id)
        
    elif scope_type == 'KEYWORD':
        keywords = keywords.filter(id=scope_id)
        # Locations matching the keyword's region, platform, category
        kw = keywords.first()
        if kw:
            locations = Location.objects.filter(
                category=kw.category,
                platform=kw.platform,
                region=kw.region
            )
        else:
            locations = Location.objects.none()
            
    elif scope_type == 'LOCATION':
        # scope_id is the Location ID. But we also need the keyword ID.
        # So for LOCATION, scope_id might be a composite like "keyword_id:location_id"
        # Let's split it:
        if ':' in str(scope_id):
            kw_id, loc_id = str(scope_id).split(':')
            keywords = keywords.filter(id=kw_id)
            locations = Location.objects.filter(id=loc_id)
        else:
            keywords = Keyword.objects.none()
            locations = Location.objects.none()
    
    else:
        keywords = Keyword.objects.none()
        locations = Location.objects.none()

    # Pre-fetch locations and map them by (category_id, platform_id, region_id)
    # Actually, we just need a flat list of location_ids for ExecutionManager
    location_ids = []
    
    # Using the same mapping logic to ensure we only get valid keyword/location matches
    loc_map = {}
    for loc in locations:
        key = (loc.category_id, loc.platform_id, loc.region_id)
        if key not in loc_map:
            loc_map[key] = []
        loc_map[key].append(loc)
        
    for kw in keywords:
        key = (kw.category_id, kw.platform_id, kw.region_id)
        matched_locations = loc_map.get(key, [])
        for loc in matched_locations:
            location_ids.append(loc.id)
            
    # Deduplicate location IDs
    location_ids = list(set(location_ids))
    
    if not location_ids:
        logger.warning(f"No locations found for scope {scope_type}:{scope_id}")
        return None
        
    from experience_cloud.executions.services import ExecutionManager
    
    execution = ExecutionManager.start_data_dump(
        user=request_user,
        scope_type=scope_type,
        scope_id=scope_id,
        location_ids=location_ids
    )
    
    if not execution:
        logger.info(f"Execution {scope_type}:{scope_id} was requested but all locations are already running.")
        return None
        
    return execution
