from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.db.models import Prefetch

from experience_cloud.catalog.models import Keyword, Location, Platform
from core.categories.models import Category
from experience_cloud.executions.models import ActiveExecution, DataDumpTask

class HierarchyCategoryListView(APIView):
    """
    Returns categories that have keywords associated with them.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
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
    """
    Returns platforms that are associated with keywords in a specific category.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        category_id = request.query_params.get('category')
        if not category_id:
            return Response({"error": "category is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        platform_ids = Keyword.objects.filter(category_id=category_id).values_list('platform_id', flat=True).distinct()
        platforms = Platform.objects.filter(id__in=platform_ids)
        
        data = [
            {
                "id": plat.id,
                "name": plat.name,
                "code": plat.code,
                "keywords_count": Keyword.objects.filter(category_id=category_id, platform_id=plat.id).count()
            }
            for plat in platforms
        ]
        return Response({"results": data})


class HierarchyKeywordListView(APIView):
    """
    Returns keywords for a specific category and platform.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        category_id = request.query_params.get('category')
        platform_id = request.query_params.get('platform')
        
        if not category_id or not platform_id:
            return Response({"error": "category and platform are required"}, status=status.HTTP_400_BAD_REQUEST)
        
        keywords = Keyword.objects.filter(category_id=category_id, platform_id=platform_id).select_related('region')
        
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
                "region_id": kw.region_id,
                "region_name": kw.region.name if kw.region else None
            })
            
            # Locations match on category, platform, and region
            grouped_data[k_str]["locations_count"] += Location.objects.filter(
                category_id=category_id,
                platform_id=platform_id,
                region_id=kw.region_id
            ).count()
            
        # Convert dict to list
        data = []
        for v in grouped_data.values():
            data.append(v)
            
        # Sort alphabetically by keyword
        data.sort(key=lambda x: x['keyword'].lower())
        
        return Response({"results": data})


class HierarchyLocationListView(APIView):
    """
    Returns locations matching the specific criteria.
    Requires category, platform, and region (since location doesn't link directly to keyword).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        category_id = request.query_params.get('category')
        platform_id = request.query_params.get('platform')
        # Instead of 'region', we accept 'keyword_ids' to properly scope tasks
        keyword_ids_param = request.query_params.get('keyword_ids')
        
        if not all([category_id, platform_id, keyword_ids_param]):
            return Response({"error": "category, platform, and keyword_ids are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        kw_ids = keyword_ids_param.split(',')
        
        # Get regions for these keywords to filter locations
        keywords = Keyword.objects.filter(id__in=kw_ids)
        region_ids = keywords.values_list('region_id', flat=True)
            
        from django.db.models import OuterRef, Subquery, IntegerField, CharField, FloatField, DateTimeField
        from experience_cloud.market_data.models import ApiDump
        
        # 100% Status Isolation: Filter the Subquery by the exact keyword IDs!
        latest_dump = ApiDump.objects.filter(
            location_id=OuterRef('pk'),
            keyword_id__in=kw_ids
        ).order_by('-created_at')

        locations = Location.objects.filter(
            category_id=category_id,
            platform_id=platform_id,
            region_id__in=region_ids
        ).annotate(
            latest_status=Subquery(latest_dump.values('status')[:1], output_field=CharField()),
            latest_products=Subquery(latest_dump.values('products_found')[:1], output_field=IntegerField()),
            latest_error=Subquery(latest_dump.values('error_message')[:1], output_field=CharField()),
            latest_response_time=Subquery(latest_dump.values('response_time')[:1], output_field=FloatField()),
            latest_run_at=Subquery(latest_dump.values('created_at')[:1], output_field=DateTimeField()),
            api_provider_name=Subquery(latest_dump.values('api_provider__name')[:1], output_field=CharField())
        )
        
        data = []
        for loc in locations:
            data.append({
                "id": loc.id,
                "pincode": loc.pincode,
                "address": loc.address,
                "latest_status": loc.latest_status,
                "latest_products": loc.latest_products or 0,
                "latest_error": loc.latest_error,
                "response_time": loc.latest_response_time,
                "last_run_at": loc.latest_run_at,
                "api_provider": loc.api_provider_name
            })
            
        return Response({"results": data})


from experience_cloud.market_data.services import trigger_data_dump

class RunDataDumpView(APIView):
    """
    Triggers the data dump execution for a given scope.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
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
    """
    Returns a list of products from the secondary database.
    """
    from experience_cloud.market_data.models import Product
    from experience_cloud.market_data.serializers import ProductSerializer
    queryset = Product.objects.all().order_by('-created_at')
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Normally we use pagination/filters, which are configured globally in settings.

class ProductsDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a product from the secondary database.
    """
    from experience_cloud.market_data.models import Product
    from experience_cloud.market_data.serializers import ProductSerializer
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    # We can also add search fields and filter fields if needed.
    search_fields = ['title', 'brand', 'keyword', 'platform', 'location']
    filterset_fields = ['platform', 'category', 'brand']


from django.db.models import Count, Q, Sum, Subquery, OuterRef, CharField, FloatField, IntegerField
from django.db.models.functions import Coalesce

class MarketDataStatsView(APIView):
    """
    Returns aggregated data dump status counts at the Category, Platform, and Region (Keyword) levels.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from experience_cloud.market_data.models import ApiDump
        from experience_cloud.catalog.models import Location
        
        # Get the latest status per location
        latest_dump = ApiDump.objects.filter(
            location_id=OuterRef('pk')
        ).order_by('-created_at')

        # Annotate each location with its latest ApiDump info
        locations = Location.objects.annotate(
            latest_status=Subquery(latest_dump.values('status')[:1], output_field=CharField()),
            latest_time=Subquery(latest_dump.values('response_time')[:1], output_field=FloatField()),
            latest_products=Subquery(latest_dump.values('products_found')[:1], output_field=IntegerField())
        )
        
        pending_q = Q(latest_status='PENDING') | Q(latest_status__isnull=True) | Q(latest_status='')
        
        # Aggregate by Category
        category_stats = locations.values('category_id').annotate(
            total=Count('id'),
            running=Count('id', filter=Q(latest_status='RUNNING')),
            pending=Count('id', filter=pending_q),
            success=Count('id', filter=Q(latest_status='SUCCESS')),
            failed=Count('id', filter=Q(latest_status='FAILED')),
            stopped=Count('id', filter=Q(latest_status='STOPPED')),
            total_time=Coalesce(Sum('latest_time'), 0.0),
            total_products=Coalesce(Sum('latest_products'), 0)
        )
        
        # Aggregate by Platform
        platform_stats = locations.values('category_id', 'platform_id').annotate(
            total=Count('id'),
            running=Count('id', filter=Q(latest_status='RUNNING')),
            pending=Count('id', filter=pending_q),
            success=Count('id', filter=Q(latest_status='SUCCESS')),
            failed=Count('id', filter=Q(latest_status='FAILED')),
            stopped=Count('id', filter=Q(latest_status='STOPPED')),
            total_time=Coalesce(Sum('latest_time'), 0.0),
            total_products=Coalesce(Sum('latest_products'), 0)
        )
        
        # Aggregate by Keyword (Region)
        keyword_stats = locations.values('category_id', 'platform_id', 'region_id').annotate(
            total=Count('id'),
            running=Count('id', filter=Q(latest_status='RUNNING')),
            pending=Count('id', filter=pending_q),
            success=Count('id', filter=Q(latest_status='SUCCESS')),
            failed=Count('id', filter=Q(latest_status='FAILED')),
            stopped=Count('id', filter=Q(latest_status='STOPPED')),
            total_time=Coalesce(Sum('latest_time'), 0.0),
            total_products=Coalesce(Sum('latest_products'), 0)
        )
        
        return Response({
            "categories": {str(c['category_id']): c for c in category_stats},
            "platforms": {f"{p['category_id']}_{p['platform_id']}": p for p in platform_stats},
            "keywords": {f"{k['category_id']}_{k['platform_id']}_{k['region_id']}": k for k in keyword_stats}
        })


class StopDataDumpView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        # Stop dump for a specific location
        from experience_cloud.market_data.models import ApiDump
        from experience_cloud.executions.models import DataDumpTask
        from experience_cloud.executions.services import ExecutionManager
        from celery import current_app
        from django.utils import timezone
        
        latest_dump = ApiDump.objects.filter(location_id=id).order_by('-created_at').first()
        if not latest_dump or latest_dump.status not in ['RUNNING', 'PENDING']:
            return Response({'error': 'Task is not running or pending'}, status=status.HTTP_400_BAD_REQUEST)
            
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
                current_app.control.revoke(task.celery_task_id, terminate=True)
                
            ExecutionManager._check_and_finalize(task.execution_id, DataDumpTask)
            
        return Response({'message': 'Task stopped successfully', 'status': 'STOPPED'})
