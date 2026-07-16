import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from shared.base.views import BaseViewSet
from .models import Platform, Location, Keyword
from .serializers import PlatformSerializer, LocationSerializer, KeywordSerializer
from .services import CatalogService

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="List Platforms"),
    retrieve=extend_schema(summary="Get Platform"),
    create=extend_schema(summary="Create Platform"),
    update=extend_schema(summary="Update Platform"),
    partial_update=extend_schema(summary="Partial Update Platform"),
    destroy=extend_schema(summary="Delete Platform")
)
class PlatformViewSet(BaseViewSet):
    queryset = Platform.objects.all().order_by('name')
    serializer_class = PlatformSerializer
    search_fields = ('name', 'code', 'value')
    ordering_fields = ('name', 'created_at', 'updated_at', 'status')


@extend_schema_view(
    list=extend_schema(summary="List Locations"),
    retrieve=extend_schema(summary="Get Location"),
    create=extend_schema(summary="Create Location"),
    update=extend_schema(summary="Update Location"),
    partial_update=extend_schema(summary="Partial Update Location"),
    destroy=extend_schema(summary="Delete Location")
)
class LocationViewSet(BaseViewSet):
    queryset = Location.objects.all().select_related('region', 'platform', 'category')
    serializer_class = LocationSerializer
    search_fields = ('pincode', 'address')
    ordering_fields = ('pincode', 'created_at', 'updated_at')

    @extend_schema(summary="Upload Locations CSV")
    @action(detail=False, methods=['post'], url_path='upload-csv')
    def upload_locations_csv(self, request):
        category_id = request.data.get('category_id')
        region_id = request.data.get('region_id')
        platform_id = request.data.get('platform_id')
        csv_file = request.FILES.get('file')

        if not csv_file:
            return Response(
                {'detail': 'file is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = CatalogService.process_locations_csv(csv_file, category_id, region_id, platform_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(summary="List Keywords"),
    retrieve=extend_schema(summary="Get Keyword"),
    create=extend_schema(summary="Create Keyword"),
    update=extend_schema(summary="Update Keyword"),
    partial_update=extend_schema(summary="Partial Update Keyword"),
    destroy=extend_schema(summary="Delete Keyword")
)
class KeywordViewSet(BaseViewSet):
    queryset = Keyword.objects.all().select_related('region', 'platform', 'category')
    serializer_class = KeywordSerializer
    search_fields = ('keyword',)
    ordering_fields = ('keyword', 'display_order', 'created_at')

    @extend_schema(summary="Upload Keywords CSV")
    @action(detail=False, methods=['post'], url_path='upload-csv')
    def upload_keywords_csv(self, request):
        category_id = request.data.get('category_id')
        region_id = request.data.get('region_id')
        platform_id = request.data.get('platform_id')
        csv_file = request.FILES.get('file')

        if not csv_file:
            return Response(
                {'detail': 'file is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = CatalogService.process_keywords_csv(csv_file, category_id, region_id, platform_id)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
