import logging
from typing import ClassVar

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authentication.permissions import AppPermissions
from shared.base.views import BaseViewSet
from shared.permissions import HasPermission

from .models import JsonTemplate, RegionJsonFile
from .serializers import JsonTemplateSerializer, RegionJsonFileSerializer

logger = logging.getLogger(__name__)

class JsonTemplateViewSet(BaseViewSet):
    """Manage CRUD operations and status toggling for JSON generation templates."""
    action_permission_mapping: ClassVar[dict] = {
        'set_status': AppPermissions.UPDATE_JSON_TEMPLATE,
        'run': AppPermissions.START_EXECUTION,
        'stop': AppPermissions.STOP_EXECUTION,
    }
    permission_mapping: ClassVar[dict] = {
        'GET': AppPermissions.READ_JSON_TEMPLATES,
        'POST': AppPermissions.CREATE_JSON_TEMPLATE,
        'PUT': AppPermissions.UPDATE_JSON_TEMPLATE,
        'PATCH': AppPermissions.UPDATE_JSON_TEMPLATE,
        'DELETE': AppPermissions.DELETE_JSON_TEMPLATE,
    }

    queryset = JsonTemplate.objects.all().order_by('id')
    serializer_class = JsonTemplateSerializer
    ordering_fields = ('id', 'name', 'template', 'process_type', 'file_format', 'created_at')
    filterset_fields: ClassVar[tuple] = ('template', 'process_type', 'file_format', 'is_active')
    search_fields = ('name', 'template')

    @action(detail=False, methods=['get'], url_path='form-options')
    def form_options(self, request, *args, **kwargs):
        """Return all valid enums for the frontend form in a single request."""
        from .models import TemplateCodes, ParentFolderCodes, ProcessTypeCodes, FormatCodes
        
        return Response({
            "templateCodes": [{"id": k, "name": v} for k, v in TemplateCodes.choices],
            "parentFolders": [{"id": k, "name": v} for k, v in ParentFolderCodes.choices],
            "processTypes": [{"id": k, "name": v} for k, v in ProcessTypeCodes.choices],
            "formats": [{"id": k, "name": v} for k, v in FormatCodes.choices]
        })

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, *args, **kwargs):
        """Set the active status of a JSON template."""
        instance = self.get_object()
        is_active = request.data.get('is_active')
        if is_active is not None:
            instance.is_active = is_active
            instance.save(update_fields=['is_active'])
            return Response({'status': 'status updated', 'is_active': instance.is_active})
        return Response({'error': 'is_active field is required'}, status=400)

    permission_classes = (IsAuthenticated,)


class RegionJsonFileViewSet(BaseViewSet):
    """Manage Region-specific JSON payload file statuses and trigger manual build executions."""
    action_permission_mapping: ClassVar[dict] = {
        'run_json_build': AppPermissions.START_EXECUTION,
        'stop_json_build': AppPermissions.STOP_EXECUTION,
    }
    permission_mapping: ClassVar[dict] = {
        'GET': AppPermissions.READ_JSON_GENERATION,
        'POST': AppPermissions.MANAGE_TAXONOMY,
        'PUT': AppPermissions.MANAGE_TAXONOMY,
        'PATCH': AppPermissions.MANAGE_TAXONOMY,
        'DELETE': AppPermissions.MANAGE_TAXONOMY,
    }
    queryset = RegionJsonFile.objects.all()
    serializer_class = RegionJsonFileSerializer
    permission_classes = (IsAuthenticated,)
    search_fields = ('template__name', 'file_name')
    ordering_fields = ('last_generated_at', 'template__name', 'file_name')
    filterset_fields = ('region',)

    def get_queryset(self):
        """Get the base queryset and auto-create missing files for a region if requested."""
        qs = super().get_queryset()
        region_id = self.request.query_params.get('region')
        if region_id:
            # Auto-create missing files for this region
            templates = JsonTemplate.objects.all()
            existing_files = qs.filter(region_id=region_id).select_related('template')
            existing_template_ids = [f.template_id for f in existing_files]

            missing = []
            for template in templates:
                if template.id not in existing_template_ids:
                    missing.append(RegionJsonFile(region_id=region_id, template=template))

            if missing:
                RegionJsonFile.objects.bulk_create(missing)
                # Re-fetch after creation
                existing_files = super().get_queryset().filter(region_id=region_id).select_related('template')

            return existing_files.order_by('template__name')

        return qs.order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='run')
    def run_json_build(self, request):
        """Manually trigger JSON generation.

        Accepts scope_type: 'ORGANIZATION', 'BRAND', 'REGION', or 'FILE'
        and scope_id.
        """
        scope_type = request.data.get('scope_type')
        scope_id = request.data.get('scope_id')
        target = request.data.get('target', 'all')

        if not scope_type or not scope_id:
            return Response({'error': 'scope_type and scope_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        scope_type = scope_type.upper()
        valid_scopes = ['ORGANIZATION', 'BRAND', 'REGION', 'FILE']
        if scope_type not in valid_scopes:
            return Response({'error': f'scope_type must be one of {valid_scopes}'}, status=status.HTTP_400_BAD_REQUEST)

        # Group files by region
        region_groups = {}
        if scope_type == 'REGION':
            files = RegionJsonFile.objects.filter(region_id=scope_id)
        elif scope_type == 'FILE':
            files = RegionJsonFile.objects.filter(id=scope_id)
        elif scope_type == 'BRAND':
            files = RegionJsonFile.objects.filter(region__brand_id=scope_id)
        elif scope_type == 'ORGANIZATION':
            files = RegionJsonFile.objects.filter(region__brand__organization_id=scope_id)
        else:
            files = RegionJsonFile.objects.none()

        # Exclude files that are already running or pending to prevent duplicate tasks
        files = files.exclude(status__in=['RUNNING', 'PENDING']).select_related('template', 'region')

        # If it's a bulk run (Region, Brand, Org), only run 'automatic' templates
        if scope_type != 'FILE':
            files = files.filter(template__process_type='automatic')

        for f in files:
            reg_id = f.region.id
            if reg_id not in region_groups:
                region_groups[reg_id] = []
            region_groups[reg_id].append({
                'template': f.template.template,
                'resource_name': f.template.name,
                'file_id': f.id,
                'target': target
            })

        if not region_groups:
            return Response({'error': 'No files found for this scope'}, status=status.HTTP_404_NOT_FOUND)

        # Calculate scope_name
        scope_name = None
        if scope_type == 'REGION':
            from core.organizations.models import Region
            scope_name = Region.objects.filter(id=scope_id).values_list('name', flat=True).first()
        elif scope_type == 'BRAND':
            from core.organizations.models import Brand
            scope_name = Brand.objects.filter(id=scope_id).values_list('name', flat=True).first()
        elif scope_type == 'ORGANIZATION':
            from core.organizations.models import Organization
            scope_name = Organization.objects.filter(id=scope_id).values_list('name', flat=True).first()
        elif scope_type == 'FILE':
            first_file = files.first()
            scope_name = first_file.template.name if first_file else f"File {scope_id}"

        # Import locally to avoid circular dependencies if needed
        # (though we only import ExecutionManager, which shouldn't import this file)
        from experience_cloud.executions.services import ExecutionManager

        execution = ExecutionManager.start_json_build(
            user=request.user,
            scope_type=scope_type,
            scope_id=scope_id,
            region_groups=region_groups,
            scope_name=scope_name
        )

        if not execution:
            return Response({'error': 'Failed to create execution'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'message': 'JSON build triggered successfully',
            'execution_id': execution.id,
            'status': execution.status
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='stop')
    def stop_json_build(self, request, id=None, **kwargs):
        """Stop a running JSON generation task."""
        file = self.get_object()

        if file.status not in ['RUNNING', 'PENDING']:
            return Response({'error': 'Task is not running or pending'}, status=status.HTTP_400_BAD_REQUEST)

        from celery import current_app
        from django.utils import timezone

        from experience_cloud.executions.models import JsonFileTask
        from experience_cloud.executions.services import ExecutionManager

        task = JsonFileTask.objects.filter(id=file.task_id).first()

        file.status = 'STOPPED'
        file.error_message = 'Manually stopped by user'
        file.save(update_fields=['status', 'error_message', 'updated_at'])

        if task:
            task.status = 'STOPPED'
            task.error_message = 'Manually stopped by user'
            task.completed_at = timezone.now()
            task.save(update_fields=['status', 'error_message', 'completed_at'])

            if task.celery_task_id:
                current_app.control.revoke(task.celery_task_id, terminate=True)

            ExecutionManager._check_and_finalize(task.execution_id, JsonFileTask)

        return Response({'message': 'Task stopped successfully', 'status': 'STOPPED'})



class DebugRunJsonBuildView(APIView):
    """Synchronously run JSON generation for debugging.

    Unauthenticated to easily hit via Postman/cURL.
    """
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        """Run the JSON generation pipeline synchronously."""
        template_name = request.data.get('template_name')
        region_id = request.data.get('region_id')

        if not template_name or not region_id:
            return Response({'error': 'template_name and region_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import time

            from experience_cloud.json_generator.builders import get_builder_for_template
            from experience_cloud.json_generator.collectors import get_all_products
            from experience_cloud.json_generator.tasks import get_region_data
            from experience_cloud.json_generator.utils import save_region_template

            # 1. Load region memory data
            region_data = get_region_data(region_id)

            # 2. Get product generator (yields from DB)
            product_generator = get_all_products(region_data)

            # 3. Get appropriate builder
            builder_func = get_builder_for_template(template_name)

            start_time = time.time()

            # 4. Generate JSON payload
            is_file_saved, json_payload = builder_func(
                region_data=region_data,
                task=None,  # No task ID for synchronous debug
                products=product_generator,
                template=template_name
            )

            brand_name = region_data.get("brand_name", "unknown")
            region_name = region_data.get("region_name", "unknown")

            # 5. Save the file if not already saved by builder
            if not is_file_saved:
                file_name, file_path = save_region_template(json_payload, brand_name, template_name, region_name)
            else:
                file_name = json_payload.get("file_name") if isinstance(json_payload, dict) else None
                file_path = json_payload.get("file_path") if isinstance(json_payload, dict) else None

            duration = time.time() - start_time

            # Cleanup generator resources
            if hasattr(product_generator, 'cleanup'):
                product_generator.cleanup()

            return Response({
                'message': 'Debug JSON build completed successfully (Synchronous)',
                'file_name': file_name,
                'file_path': file_path,
                'duration_seconds': round(duration, 2)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Debug JSON build failed")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class JsonGenerationStatsView(APIView):
    """Returns aggregated JSON generation status counts at the Organization, Brand, and Region levels.

    This solves N+1 problems and ensures UI performance remains high.
    """
    from shared.serializers import EmptySerializer
    serializer_class = EmptySerializer
    permission_classes = (IsAuthenticated, HasPermission)
    required_permission = AppPermissions.READ_JSON_GENERATION

    def get(self, request, *args, **kwargs):
        """Get the stats."""
        # Base queries to count the statuses
        pending_q = Q(status='PENDING') | Q(status__isnull=True) | Q(status='')

        region_stats = RegionJsonFile.objects.values('region_id').annotate(
            total=Count('id'),
            running=Count('id', filter=Q(status='RUNNING')),
            pending=Count('id', filter=pending_q),
            success=Count('id', filter=Q(status='SUCCESS')),
            failed=Count('id', filter=Q(status='FAILED')),
            stopped=Count('id', filter=Q(status='STOPPED')),
            total_size=Coalesce(Sum('file_size'), 0),
            total_duration=Coalesce(Sum('generation_duration'), 0.0)
        )

        brand_stats = RegionJsonFile.objects.values('region__brand_id').annotate(
            total=Count('id'),
            running=Count('id', filter=Q(status='RUNNING')),
            pending=Count('id', filter=pending_q),
            success=Count('id', filter=Q(status='SUCCESS')),
            failed=Count('id', filter=Q(status='FAILED')),
            stopped=Count('id', filter=Q(status='STOPPED')),
            total_size=Coalesce(Sum('file_size'), 0),
            total_duration=Coalesce(Sum('generation_duration'), 0.0)
        )

        org_stats = RegionJsonFile.objects.values('region__brand__organization_id').annotate(
            total=Count('id'),
            running=Count('id', filter=Q(status='RUNNING')),
            pending=Count('id', filter=pending_q),
            success=Count('id', filter=Q(status='SUCCESS')),
            failed=Count('id', filter=Q(status='FAILED')),
            stopped=Count('id', filter=Q(status='STOPPED')),
            total_size=Coalesce(Sum('file_size'), 0),
            total_duration=Coalesce(Sum('generation_duration'), 0.0)
        )

        return Response({
            'organizations': {
                str(item['region__brand__organization_id']): item
                for item in org_stats if item['region__brand__organization_id']
            },
            'brands': {
                str(item['region__brand_id']): item
                for item in brand_stats if item['region__brand_id']
            },
            'regions': {
                str(item['region_id']): item
                for item in region_stats if item['region_id']
            }
        })
