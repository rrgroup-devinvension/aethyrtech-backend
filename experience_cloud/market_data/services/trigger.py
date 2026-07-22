import logging
from django.utils import timezone
from experience_cloud.executions.models import ActiveExecution, DataDumpTask
from experience_cloud.catalog.models import Keyword, Location
from django.db.models import Q

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
        locations = Location.objects.filter(category_id=scope_id)
    
    elif scope_type == 'PLATFORM':
        if ':' in str(scope_id):
            cat_id, plat_id = str(scope_id).split(':')
            keywords = keywords.filter(category_id=cat_id, platform_id=plat_id)
            locations = Location.objects.filter(category_id=cat_id, platform_id=plat_id)
        else:
            keywords = keywords.filter(platform_id=scope_id)
            locations = Location.objects.filter(platform_id=scope_id)
        
    elif scope_type == 'KEYWORD':
        if ',' in str(scope_id):
            kw_ids = str(scope_id).split(',')
            keywords = keywords.filter(id__in=kw_ids)
        else:
            keywords = keywords.filter(id=scope_id)
            
        kw_combos = keywords.values('category_id', 'platform_id', 'region_id')
        q_obj = Q()
        for c in kw_combos:
            q_obj |= Q(category_id=c['category_id'], platform_id=c['platform_id'], region_id=c['region_id'])
            
        if q_obj:
            locations = Location.objects.filter(q_obj)
        else:
            locations = Location.objects.none()
            
    elif scope_type == 'LOCATION':
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

    platform_ids = {kw.platform_id for kw in keywords if kw.platform_id}
    from experience_cloud.catalog.models import Platform
    api_providers = dict(Platform.objects.filter(id__in=platform_ids).values_list('id', 'api_provider_id'))

    task_pairs = []
    
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
            task_pairs.append({
                'keyword_id': kw.id, 
                'location_id': loc.id,
                'platform_id': kw.platform_id,
                'api_provider_id': api_providers.get(kw.platform_id)
            })
            
    # Deduplicate task pairs
    unique_pairs = []
    seen = set()
    for pair in task_pairs:
        tup = (pair['keyword_id'], pair['location_id'])
        if tup not in seen:
            seen.add(tup)
            unique_pairs.append(pair)
    
    if not unique_pairs:
        logger.warning(f"No valid keyword+location combinations found for scope {scope_type}:{scope_id}")
        return None
        
    # Calculate scope name for UI
    scope_name = None
    if scope_type == 'LOCATION' and ':' in str(scope_id):
        kw_name = keywords.first().keyword if keywords.exists() else 'Unknown Keyword'
        loc = locations.first()
        loc_name = 'Unknown Location'
        if loc:
            loc_name = str(loc.pincode) if loc.pincode else str(loc.address)
        scope_name = f"{kw_name} / {loc_name}"
    elif scope_type == 'CATEGORY':
        from experience_cloud.catalog.models import Category
        scope_name = Category.objects.filter(id=scope_id).values_list('name', flat=True).first()
    elif scope_type == 'REGION':
        from experience_cloud.catalog.models import Region
        scope_name = Region.objects.filter(id=scope_id).values_list('name', flat=True).first()
    elif scope_type == 'KEYWORD':
        scope_name = keywords.first().keyword if keywords.exists() else None
    elif scope_type == 'LOCATION':
        loc = locations.first()
        scope_name = (str(loc.pincode) if loc.pincode else str(loc.address)) if loc else None

    from experience_cloud.executions.services import ExecutionManager
    
    execution = ExecutionManager.start_data_dump(
        user=request_user,
        scope_type=scope_type,
        scope_id=scope_id,
        task_pairs=unique_pairs,
        scope_name=scope_name
    )
    
    if not execution:
        logger.info(f"Execution {scope_type}:{scope_id} was requested but all tasks are already running.")
        return None
        
    return execution
