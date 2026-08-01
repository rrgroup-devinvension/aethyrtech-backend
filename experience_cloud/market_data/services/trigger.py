import logging

from django.db.models import Q

from experience_cloud.catalog.models import Keyword, Location

logger = logging.getLogger(__name__)

def trigger_data_dump(scope_type, scope_id, request_user=None):
    """Initiate a data dump execution sequence for a given entity scope.

    Parses the dynamic scope (Category, Platform, Keyword, Location, Region) to systematically
    identify all valid keyword-location combinations. Generates distinct tasks, establishes a
    tracking mechanism in the execution manager, and orchestrates the distributed scraping workflow.

    Args:
        scope_type (str): The hierarchical level triggering the execution (e.g., 'CATEGORY', 'KEYWORD').
        scope_id (str): The primary key or composite identifier (e.g., 'cat_id:plat_id') of the target scope.
        request_user (User, optional): The authenticated user initiating the request for audit tracing.

    Returns:
        ActiveExecution | None: The spawned execution orchestrator instance, or None if validation fails.
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
            q_obj.add(Q(category_id=c['category_id'], platform_id=c['platform_id'], region_id=c['region_id']), Q.OR)

        locations = Location.objects.filter(q_obj) if q_obj else Location.objects.none()

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

    task_pairs_dict = {}

    loc_map = {}
    for loc in locations:
        key = (getattr(loc, 'category_id', None), getattr(loc, 'platform_id', None), getattr(loc, 'region_id', None))
        if key not in loc_map:
            loc_map[key] = []
        loc_map[key].append(loc)

    for kw in keywords:
        key = (getattr(kw, 'category_id', None), getattr(kw, 'platform_id', None), getattr(kw, 'region_id', None))
        matched_locations = loc_map.get(key, [])
        for loc in matched_locations:
            loc_name = loc.pincode if loc.pincode else loc.address

            # Use string representations for grouping
            group_key = (kw.category_id, kw.platform_id, kw.keyword, loc_name)

            if group_key not in task_pairs_dict:
                task_pairs_dict[group_key] = {
                    'category_id': kw.category_id,
                    'platform_id': kw.platform_id,
                    'api_provider_id': api_providers.get(kw.platform_id),
                    'keyword_name': kw.keyword,
                    'location_name': loc_name,
                    'regions': []
                }

            # Avoid duplicate region entries within the same group
            region_id = getattr(kw, 'region_id', None)
            if region_id and not any(r['region_id'] == region_id for r in task_pairs_dict[group_key]['regions']):
                brand_id = kw.region.brand_id if (kw.region and hasattr(kw.region, 'brand_id')) else None
                brand_name = (
                    kw.region.brand.name
                    if (kw.region and hasattr(kw.region, 'brand') and kw.region.brand)
                    else ""
                )
                region_name = kw.region.name if kw.region else ""

                task_pairs_dict[group_key]['regions'].append({
                    'region_id': region_id,
                    'region_name': region_name,
                    'brand_id': brand_id,
                    'brand_name': brand_name
                })

    unique_pairs = list(task_pairs_dict.values())

    if not unique_pairs:
        logger.warning(f"No valid keyword+location combinations found for scope {scope_type}:{scope_id}")
        return None

    # Calculate scope name for UI
    scope_name = None
    if scope_type == 'LOCATION' and ':' in str(scope_id):
        kw_first = keywords.first()
        kw_name = kw_first.keyword if kw_first else 'Unknown Keyword'
        loc = locations.first()
        loc_name = 'Unknown Location'
        if loc:
            loc_name = loc.pincode if loc.pincode else loc.address
        scope_name = f"{kw_name} / {loc_name}"
    elif scope_type == 'CATEGORY':
        from core.categories.models import Category
        scope_name = Category.objects.filter(id=scope_id).values_list('name', flat=True).first()
    elif scope_type == 'REGION':
        from core.organizations.models import Region
        scope_name = Region.objects.filter(id=scope_id).values_list('name', flat=True).first()
    elif scope_type == 'PLATFORM':
        from experience_cloud.catalog.models import Platform
        plat_id = str(scope_id).split(':')[1] if ':' in str(scope_id) else scope_id
        scope_name = Platform.objects.filter(id=plat_id).values_list('name', flat=True).first()
    elif scope_type == 'KEYWORD':
        kw_first = keywords.first()
        scope_name = kw_first.keyword if kw_first else None
    elif scope_type == 'LOCATION':
        loc = locations.first()
        scope_name = (loc.pincode if loc.pincode else loc.address) if loc else None

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
