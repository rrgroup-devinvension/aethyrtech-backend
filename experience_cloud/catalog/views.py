from core.authentication.permissions import AppPermissions
import logging
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from shared.base.views import BaseViewSet
from .models import Platform, Location, Keyword
from .serializers import PlatformSerializer, LocationSerializer, KeywordSerializer
from .services import BulkDataService

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
    action_permission_mapping = {
        'upload-file': AppPermissions.CREATE_PLATFORM,
        'export-data': AppPermissions.READ_PLATFORMS,
        'download-template': AppPermissions.READ_PLATFORMS,
        'bulk-delete': AppPermissions.DELETE_PLATFORM,
    }
    
    permission_mapping = {
        'GET': AppPermissions.READ_PLATFORMS,
        'POST': AppPermissions.CREATE_PLATFORM,
        'PUT': AppPermissions.UPDATE_PLATFORM,
        'PATCH': AppPermissions.UPDATE_PLATFORM,
        'DELETE': AppPermissions.DELETE_PLATFORM
    }

    queryset = Platform.objects.select_related('api_provider').all().order_by('name')
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
    action_permission_mapping = {
        'upload_file': AppPermissions.MANAGE_TAXONOMY,
        'export_data': AppPermissions.READ_TAXONOMY,
        'download_template': AppPermissions.READ_TAXONOMY,
        'bulk_delete': AppPermissions.MANAGE_TAXONOMY,
    }
    permission_mapping = {
        'GET': AppPermissions.READ_TAXONOMY,
        'POST': AppPermissions.MANAGE_TAXONOMY,
        'PUT': AppPermissions.MANAGE_TAXONOMY,
        'PATCH': AppPermissions.MANAGE_TAXONOMY,
        'DELETE': AppPermissions.MANAGE_TAXONOMY
    }
    queryset = Location.objects.all().select_related('region', 'platform', 'category')
    serializer_class = LocationSerializer
    search_fields = ('pincode', 'address')
    ordering_fields = ('pincode', 'address', 'platform__name', 'category__name', 'created_at', 'updated_at')
    filterset_fields = ['platform', 'category', 'region']

    @extend_schema(summary="Upload Locations File")
    @action(detail=False, methods=['post'], url_path='upload-file')
    def upload_file(self, request):
        category_id = request.data.get('category_id')
        region_id = request.data.get('region_id')
        platform_ids = request.data.getlist('platform_id')
        file = request.FILES.get('file')

        if not file:
            return Response({'detail': 'file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = BulkDataService.process_locations_file(file, file.name, category_id, region_id, platform_ids)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Export Locations Data")
    @action(detail=False, methods=['get'], url_path='export-data')
    def export_data(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        format_type = request.query_params.get('format', 'xlsx')
        columns = [('pincode', 'pincode'), ('address', 'address'), ('lat', 'lat'), ('lng', 'lng')]
        
        category_id = request.query_params.get('category')
        region_id = request.query_params.get('region')
        platform_id = request.query_params.get('platform')
        filename = BulkDataService.generate_export_filename('locations', category_id, region_id, platform_id)
        
        return BulkDataService.generate_export_response(queryset, filename, columns, format_type)

    @extend_schema(summary="Download Locations Template")
    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        format_type = request.query_params.get('format', 'xlsx')
        columns = ['pincode', 'address', 'lat', 'lng']
        return BulkDataService.generate_template_response('locations_template', columns, format_type)

    @extend_schema(summary="Bulk Delete Locations")
    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'detail': 'No ids provided.'}, status=status.HTTP_400_BAD_REQUEST)
        Location.objects.filter(id__in=ids).delete()
        return Response({'detail': f'Deleted {len(ids)} locations.'}, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List Keywords"),
    retrieve=extend_schema(summary="Get Keyword"),
    create=extend_schema(summary="Create Keyword"),
    update=extend_schema(summary="Update Keyword"),
    partial_update=extend_schema(summary="Partial Update Keyword"),
    destroy=extend_schema(summary="Delete Keyword")
)
class KeywordViewSet(BaseViewSet):
    action_permission_mapping = {
        'upload_file': AppPermissions.MANAGE_TAXONOMY,
        'export_data': AppPermissions.READ_TAXONOMY,
        'download_template': AppPermissions.READ_TAXONOMY,
        'bulk_delete': AppPermissions.MANAGE_TAXONOMY,
    }
    permission_mapping = {
        'GET': AppPermissions.READ_TAXONOMY,
        'POST': AppPermissions.MANAGE_TAXONOMY,
        'PUT': AppPermissions.MANAGE_TAXONOMY,
        'PATCH': AppPermissions.MANAGE_TAXONOMY,
        'DELETE': AppPermissions.MANAGE_TAXONOMY
    }
    queryset = Keyword.objects.all().select_related('region', 'platform', 'category')
    serializer_class = KeywordSerializer
    search_fields = ('keyword',)
    ordering_fields = ('keyword', 'platform__name', 'category__name', 'display_order', 'created_at')
    filterset_fields = ['platform', 'category', 'region']

    @extend_schema(summary="Upload Keywords File")
    @action(detail=False, methods=['post'], url_path='upload-file')
    def upload_file(self, request):
        category_id = request.data.get('category_id')
        region_id = request.data.get('region_id')
        platform_ids = request.data.getlist('platform_id')
        file = request.FILES.get('file')

        if not file:
            return Response({'detail': 'file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = BulkDataService.process_keywords_file(file, file.name, category_id, region_id, platform_ids)
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Export Keywords Data")
    @action(detail=False, methods=['get'], url_path='export-data')
    def export_data(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        format_type = request.query_params.get('format', 'xlsx')
        columns = [('keyword', 'keyword')]
        
        category_id = request.query_params.get('category')
        region_id = request.query_params.get('region')
        platform_id = request.query_params.get('platform')
        filename = BulkDataService.generate_export_filename('keywords', category_id, region_id, platform_id)
        
        return BulkDataService.generate_export_response(queryset, filename, columns, format_type)

    @extend_schema(summary="Download Keywords Template")
    @action(detail=False, methods=['get'], url_path='download-template')
    def download_template(self, request):
        format_type = request.query_params.get('format', 'xlsx')
        columns = ['keyword']
        return BulkDataService.generate_template_response('keywords_template', columns, format_type)

    @extend_schema(summary="Bulk Delete Keywords")
    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'detail': 'No ids provided.'}, status=status.HTTP_400_BAD_REQUEST)
        Keyword.objects.filter(id__in=ids).delete()
        return Response({'detail': f'Deleted {len(ids)} keywords.'}, status=status.HTTP_200_OK)
