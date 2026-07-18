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
        
        data = [
            {
                "id": kw.id,
                "keyword": kw.keyword,
                "region_id": kw.region_id,
                "region_name": kw.region.name if kw.region else None,
                "locations_count": Location.objects.filter(category_id=category_id, platform_id=platform_id, region_id=kw.region_id).count()
            }
            for kw in keywords
        ]
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
        region_id = request.query_params.get('region')
        
        if not all([category_id, platform_id, region_id]):
            return Response({"error": "category, platform, and region are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        locations = Location.objects.filter(
            category_id=category_id,
            platform_id=platform_id,
            region_id=region_id
        )
        
        data = [
            {
                "id": loc.id,
                "pincode": loc.pincode,
                "address": loc.address,
            }
            for loc in locations
        ]
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
        
        return Response({
            "message": "Data Dump triggered successfully",
            "execution_id": execution.id,
            "total_tasks": execution.total_tasks
        })

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

