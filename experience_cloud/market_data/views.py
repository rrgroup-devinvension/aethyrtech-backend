from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication.permissions import AppPermissions
from core.categories.models import Category
from experience_cloud.catalog.models import Keyword, Location, Platform
from shared.permissions import HasPermission


class HierarchyCategoryListView(APIView):
    """API endpoint to retrieve a list of all active categories.

    Filters categories to only include those actively associated with configured keywords,
    providing the foundation for the cascading filter hierarchy in the frontend analytics dashboard.
    """
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.VIEW_ANALYTICS
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    def get(self, request, *args, **kwargs):
        """Get the categories list."""
        # We want to list all active categories
        categories = Category.objects.filter(status='active')

        data = [
            {
                "id": cat.id,
                "name": cat.name,
                "platforms_count": Keyword.objects.filter(category_id=cat.id).values('platform_id').distinct().count()
            }
            for cat in categories
        ]
        return Response({"results": data})


class HierarchyPlatformListView(APIView):
    """API endpoint to retrieve associated platforms for a specific category.

    Yields a distinct list of platforms tied to active keywords within the requested category,
    including api_provider metadata to support subsequent data extraction tasks.
    """
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.VIEW_ANALYTICS
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    def get(self, request, *args, **kwargs):
        """Get the platforms list."""
        category_id = request.query_params.get('category')
        if not category_id:
            return Response({"error": "category is required"}, status=status.HTTP_400_BAD_REQUEST)

        platform_ids = Keyword.objects.filter(category_id=category_id).values_list('platform_id', flat=True).distinct()
        platforms = Platform.objects.filter(id__in=platform_ids).select_related('api_provider')

        data = [
            {
                "id": plat.id,
                "name": plat.name,
                "code": plat.code,
                "api_provider_name": plat.api_provider.name if plat.api_provider else None,
                "keywords_count": Keyword.objects.filter(category_id=category_id, platform_id=plat.id).count()
            }
            for plat in platforms
        ]
        return Response({"results": data})


class HierarchyKeywordListView(APIView):
    """API endpoint to retrieve localized keywords for a category and platform.

    Groups keyword permutations by region and brand, pre-calculating the volume of
    applicable locations to inform the scale of potential data dump executions.
    """
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.VIEW_ANALYTICS
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    def get(self, request, *args, **kwargs):
        """Get the keywords for a specific category and platform."""
        category_id = request.query_params.get('category')
        platform_id = request.query_params.get('platform')

        if not category_id or not platform_id:
            return Response({"error": "category and platform are required"}, status=status.HTTP_400_BAD_REQUEST)

        keywords = Keyword.objects.filter(
            category_id=category_id, platform_id=platform_id
        ).select_related('region', 'region__brand')

        grouped_data = {}
        for kw in keywords:
            k_str = kw.keyword
            if k_str not in grouped_data:
                grouped_data[k_str] = {
                    "keyword": k_str,
                    "regions": [],
                    "locations_count": 0
                }
            grouped_data[k_str]["regions"].append({
                "keyword_id": kw.id,
                "region_id": getattr(kw, "region_id", None),
                "region_name": kw.region.name if kw.region else None,
                "brand_name": (
                    kw.region.brand.name
                    if kw.region and hasattr(kw.region, 'brand') and kw.region.brand
                    else None
                )
            })

            # Locations match on category, platform, and region
            grouped_data[k_str]["locations_count"] += Location.objects.filter(
                category_id=category_id,
                platform_id=platform_id,
                region_id=getattr(kw, "region_id", None)
            ).count()

        # Convert dict to list
        data = []
        for v in grouped_data.values():
            data.append(v)

        # Sort alphabetically by keyword
        data.sort(key=lambda x: x['keyword'].lower())

        return Response({"results": data})


class HierarchyLocationListView(APIView):
    """API endpoint to retrieve distinct geographic target locations.

    Filters locations precisely by category, platform, and optional region/brand overrides,
    providing the final leaf nodes necessary for granular API extraction tasks.
    """

    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.VIEW_ANALYTICS
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    def get(self, request, *args, **kwargs):
        """Get locations matching criteria."""
        category_id = request.query_params.get('category')
        platform_id = request.query_params.get('platform')
        # Instead of 'region', we accept 'keyword_ids' to properly scope tasks
        keyword_ids_param = request.query_params.get('keyword_ids')

        if not all([category_id, platform_id, keyword_ids_param]):
            return Response(
                {"error": "category, platform, and keyword_ids are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        kw_ids = keyword_ids_param.split(',')

        # Get regions for these keywords to filter locations
        keywords = Keyword.objects.filter(id__in=kw_ids)
        region_ids = keywords.values_list('region_id', flat=True)
        keyword_names = list(set(keywords.values_list('keyword', flat=True)))

        from experience_cloud.market_data.models import ApiDump

        locations = Location.objects.filter(
            category_id=category_id,
            platform_id=platform_id,
            region_id__in=region_ids
        )

        # Fetch ApiDumps and build a fast lookup dictionary in Python
        # This allows us to perfectly filter by region_ids (which is a JSON array)
        api_dumps = ApiDump.objects.filter(
            category_id=category_id,
            platform_id=platform_id,
            keyword_name__in=keyword_names
        ).select_related('api_provider').order_by('-created_at')

        dump_lookup = {}
        for d in api_dumps:
            loc_val = str(d.location_name) if d.location_name else ""
            kw_val = str(d.keyword_name) if d.keyword_name else ""
            for rid in (d.region_ids or []):
                key = (loc_val, kw_val, str(rid))
                if key not in dump_lookup:
                    dump_lookup[key] = d

        data = []
        for loc in locations:
            latest_match = None
            loc_name = loc.pincode if loc.pincode else loc.address
            loc_name_str = str(loc_name) if loc_name else ""

            for kw in keyword_names:
                key = (loc_name_str, str(kw), str(loc.region_id))
                match = dump_lookup.get(key)
                if match and (not latest_match or match.created_at > latest_match.created_at):
                        latest_match = match

            data.append({
                "id": loc.id,
                "pincode": loc.pincode,
                "address": loc.address,
                "latest_status": getattr(latest_match, "status", None),
                "latest_products": getattr(latest_match, "products_found", 0) or 0,
                "latest_error": getattr(latest_match, "error_message", None),
                "response_time": getattr(latest_match, "response_time", None),
                "last_run_at": getattr(latest_match, "created_at", None),
                "api_provider": latest_match.api_provider.name if latest_match and latest_match.api_provider else None
            })

        return Response({"results": data})


from experience_cloud.market_data.services.trigger import trigger_data_dump  # noqa: E402


class RunDataDumpView(APIView):
    """API endpoint to initiate a robust data extraction execution sequence.

    Validates the provided geographic scope, spawns tracking entities in the execution
    manager, and queues the operations asynchronously to the Celery broker for background processing.
    """
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.START_EXECUTION
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    def post(self, request, *args, **kwargs):
        """Trigger the data dump execution."""
        scope_type = request.data.get('scope_type')
        scope_id = request.data.get('scope_id')

        if not scope_type or not scope_id:
            return Response({"error": "scope_type and scope_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        execution = trigger_data_dump(scope_type, scope_id, request.user)

        if not execution:
            return Response({
                "message": "All requested locations are already running.",
                "execution_id": None,
                "total_tasks": 0
            }, status=status.HTTP_200_OK)

        return Response({
            "message": "Data Dump triggered successfully",
            "execution_id": execution.id,
            "total_tasks": execution.total_tasks
        }, status=status.HTTP_201_CREATED)

class ProductsListView(generics.ListAPIView):
    """API endpoint to list or filter extracted product records.

    Interfaces with the XBytes secondary database to expose recently scraped product
    details, search rankings, and raw configurations for frontend audit visualization.
    """
    from experience_cloud.market_data.serializers import ProductSerializer
    from experience_cloud.market_integrations.models.xbytes import XBytesProduct
    queryset = XBytesProduct.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.READ_PRODUCTS

    # Normally we use pagination/filters, which are configured globally in settings.

class ProductsDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API endpoint to retrieve, selectively update, or hard-delete a specific product.

    Provides granular CRUD control over individual scraped items within the secondary
    database to manually override anomalies or flag deprecated entries.
    """
    from experience_cloud.market_data.serializers import ProductSerializer
    from experience_cloud.market_integrations.models.xbytes import XBytesProduct
    queryset = XBytesProduct.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.UPDATE_PRODUCTS
    lookup_field = 'id'
    # We can also add search fields and filter fields if needed.
    search_fields = ['title', 'brand', 'keyword', 'platform', 'pincode']  # noqa: RUF012
    filterset_fields = ['platform', 'category', 'brand']  # noqa: RUF012



class MarketDataStatsView(APIView):
    """API endpoint to retrieve macro-level execution statistics.

    Aggregates realtime processing statuses (PENDING, RUNNING, SUCCESS, FAILED) across
    the Category, Platform, and Keyword hierarchies for comprehensive dashboard monitoring.
    """
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.VIEW_ANALYTICS
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    def get(self, request, *args, **kwargs):
        """Get the stats."""
        from django.db.models import F

        from experience_cloud.catalog.models import Keyword
        from experience_cloud.market_data.models import ApiDump

        # Fetch ApiDumps and build a fast lookup dictionary in Python
        # This allows us to perfectly filter by region_ids (which is a JSON array)
        api_dumps = ApiDump.objects.all().order_by('-created_at').values(
            'category_id', 'platform_id', 'keyword_name', 'location_name',
            'region_ids', 'status', 'response_time', 'products_found'
        )

        dump_lookup = {}
        for d in api_dumps:
            cat = str(d['category_id']) if d['category_id'] else ""
            plat = str(d['platform_id']) if d['platform_id'] else ""
            kw = str(d['keyword_name']) if d['keyword_name'] else ""
            loc = str(d['location_name']) if d['location_name'] else ""
            for rid in (d['region_ids'] or []):
                key = (cat, plat, kw, loc, str(rid))
                if key not in dump_lookup:
                    dump_lookup[key] = d

        # Get a row for every (Keyword, Location) pair matching the exact platform and category
        kw_locs = Keyword.objects.filter(
            platform_id=F('region__location__platform_id'),
            category_id=F('region__location__category_id')
        ).annotate(
            loc_id=F('region__location__id'),
            pincode=F('region__location__pincode'),
            address=F('region__location__address')
        ).values(
            'id', 'category_id', 'platform_id', 'region_id', 'loc_id', 'keyword', 'pincode', 'address'
        )

        category_stats = {}
        platform_stats = {}
        keyword_stats = {}

        def add_stats(target_dict, key, status, time, products):
            if key not in target_dict:
                target_dict[key] = {
                    'total': 0, 'running': 0, 'pending': 0, 'success': 0,
                    'failed': 0, 'stopped': 0, 'total_time': 0.0, 'total_products': 0
                }

            target_dict[key]['total'] += 1

            if status == 'RUNNING':
                target_dict[key]['running'] += 1
            elif status == 'SUCCESS':
                target_dict[key]['success'] += 1
            elif status == 'FAILED':
                target_dict[key]['failed'] += 1
            elif status == 'STOPPED':
                target_dict[key]['stopped'] += 1
            else:
                target_dict[key]['pending'] += 1

            target_dict[key]['total_time'] += (time or 0.0)
            target_dict[key]['total_products'] += (products or 0)

        for row in kw_locs:
            kw_id = row['id']
            cat_id = str(row['category_id'])
            plat_key = f"{row['category_id']}_{row['platform_id']}"
            kw_key = f"{row['category_id']}_{row['platform_id']}_{kw_id}"

            # Safely handle empty string pincodes like trigger.py
            loc_name = row['pincode'] if row['pincode'] else row['address']
            loc_name_str = str(loc_name) if loc_name else ""

            key = (
                str(row['category_id']),
                str(row['platform_id']),
                str(row['keyword'] if row['keyword'] else ""),
                loc_name_str,
                str(row['region_id'])
            )
            latest_dump = dump_lookup.get(key)

            if latest_dump:
                s = latest_dump['status']
                t = latest_dump['response_time']
                p = latest_dump['products_found']
            else:
                s = None
                t = 0.0
                p = 0

            add_stats(category_stats, cat_id, s, t, p)
            add_stats(platform_stats, plat_key, s, t, p)
            add_stats(keyword_stats, kw_key, s, t, p)

        return Response({
            "categories": category_stats,
            "platforms": platform_stats,
            "keywords": keyword_stats
        })


class StopDataDumpView(APIView):
    """API endpoint to gracefully interrupt an active extraction task.

    Locates the active Celery worker thread and attempts a soft termination,
    subsequently updating the execution states to prevent further scheduled retries.
    """
    permission_classes = (permissions.IsAuthenticated, HasPermission)

    required_permission = AppPermissions.STOP_EXECUTION
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer

    def post(self, request, id, *args, **kwargs):
        """Stop dump for a specific location."""
        # Stop dump for a specific location
        from celery import current_app
        from django.utils import timezone

        from experience_cloud.catalog.models import Location
        from experience_cloud.executions.models import DataDumpTask
        from experience_cloud.executions.services import ExecutionManager
        from experience_cloud.market_data.models import ApiDump

        loc = Location.objects.get(id=id)
        loc_name = loc.pincode if loc.pincode else loc.address

        keyword_id = request.data.get('keyword_id')
        keyword_name = None
        if keyword_id:
            from experience_cloud.catalog.models import Keyword
            kw = Keyword.objects.filter(id=keyword_id).first()
            if kw:
                keyword_name = kw.keyword

        filters = {
            'category_id': loc.category_id,
            'platform_id': loc.platform_id,
            'location_name': loc_name
        }
        if keyword_name:
            filters['keyword_name'] = keyword_name

        latest_dumps = ApiDump.objects.filter(**filters, status__in=['RUNNING', 'PENDING']).order_by('-created_at')

        if not latest_dumps.exists():
            return Response({'error': 'Task is not running or pending'}, status=status.HTTP_400_BAD_REQUEST)

        for latest_dump in latest_dumps:
            latest_dump.status = 'STOPPED'
            latest_dump.error_message = 'Manually stopped by user'
            latest_dump.save(update_fields=['status', 'error_message'])

            task = DataDumpTask.objects.filter(id=latest_dump.task_id).first()
            if task:
                task.status = 'STOPPED'
                task.error_message = 'Manually stopped by user'
                task.completed_at = timezone.now()
                task.save(update_fields=['status', 'error_message', 'completed_at'])

                if task.celery_task_id:
                    current_app.control.revoke(task.celery_task_id, terminate=True)  # type: ignore

                ExecutionManager._check_and_finalize(task.execution_id, DataDumpTask)

        return Response({'message': 'Task stopped successfully', 'status': 'STOPPED'})

class DebugRunDataDumpView(APIView):
    """Synchronously run a single Data Dump execution for debugging.

    Unauthenticated to easily hit via Postman/cURL.
    Accepts location_id and keyword_id.
    """
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        """Run the Data Dump synchronously."""
        location_id = request.data.get('location_id')
        keyword_id = request.data.get('keyword_id')

        if not location_id or not keyword_id:
            return Response(
                {'error': 'location_id and keyword_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            import time

            from django.core.exceptions import ObjectDoesNotExist

            from core.categories.models import Category
            from experience_cloud.catalog.models import Keyword, Location, Platform
            from experience_cloud.market_data.services.dispatcher import DataDumpDispatcher
            from experience_cloud.market_data.tasks import build_data_dump_schema

            # Fetch relevant objects
            try:
                location = Location.objects.get(id=location_id)
                keyword = Keyword.objects.get(id=keyword_id)
                platform_obj = Platform.objects.select_related('api_provider').get(id=location.platform_id)
                category_obj = Category.objects.filter(id=location.category_id).first()
                provider_obj = getattr(platform_obj, "api_provider", None) if platform_obj else None
            except ObjectDoesNotExist as e:
                return Response({'error': f'Failed to fetch configuration objects: {e!s}'}, status=404)

            loc_name = location.pincode if location.pincode else location.address

            # Construct metadata
            metadata = {
                'location_name': loc_name,
                'keyword_name': keyword.keyword,
                'regions': [location.region_id] if location.region_id else []
            }

            # Build schema exactly like the async task does
            schema = build_data_dump_schema(metadata, platform_obj, category_obj, provider_obj)

            start_time = time.time()

            # Execute synchronously
            dispatcher = DataDumpDispatcher()
            response = dispatcher.execute(schema)

            duration = time.time() - start_time

            return Response({
                'message': 'Debug Data Dump completed successfully (Synchronous)',
                'service_response': response,
                'duration_seconds': round(duration, 2)
            }, status=status.HTTP_200_OK)

        except Exception as e:  # noqa: BLE001
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
