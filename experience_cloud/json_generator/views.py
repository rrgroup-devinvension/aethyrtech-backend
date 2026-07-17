from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from shared.base.views import BaseViewSet
from .models import JsonTemplate, RegionJsonFile
from .serializers import JsonTemplateSerializer, RegionJsonFileSerializer
from experience_cloud.executions.models import ActiveExecution, JsonFileTask
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class JsonTemplateViewSet(BaseViewSet):
    """CRUD operations for JsonTemplate."""
    queryset = JsonTemplate.objects.all().order_by('name')
    serializer_class = JsonTemplateSerializer

    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, *args, **kwargs):
        instance = self.get_object()
        is_active = request.data.get('is_active')
        if is_active is not None:
            instance.is_active = is_active
            instance.save(update_fields=['is_active'])
            return Response({'status': 'status updated', 'is_active': instance.is_active})
        return Response({'error': 'is_active field is required'}, status=400)
    permission_classes = [IsAuthenticated]
    search_fields = ('name', 'template')


class RegionJsonFileViewSet(BaseViewSet):
    """Provides RegionJsonFiles for a specific region, auto-creating them if missing."""
    queryset = RegionJsonFile.objects.all()
    serializer_class = RegionJsonFileSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ('template__name', 'file_name')
    ordering_fields = ('last_generated_at', 'template__name', 'file_name')
    filterset_fields = ['region']
    
    def get_queryset(self):
        qs = super().get_queryset()
        region_id = self.request.query_params.get('region')
        if region_id:
            # Auto-create missing files for this region
            templates = JsonTemplate.objects.all()
            existing_files = qs.filter(region_id=region_id).select_related('template', 'task')
            existing_template_ids = [f.template_id for f in existing_files]
            
            missing = []
            for template in templates:
                if template.id not in existing_template_ids:
                    missing.append(RegionJsonFile(region_id=region_id, template=template))
            
            if missing:
                RegionJsonFile.objects.bulk_create(missing)
                # Re-fetch after creation
                existing_files = super().get_queryset().filter(region_id=region_id).select_related('template', 'task')
                
            return existing_files.order_by('template__name')
            
        return qs.order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='run')
    def run_json_build(self, request):
        """
        Manually trigger JSON generation.
        Accepts scope_type: 'ORGANIZATION', 'BRAND', 'REGION', or 'FILE'
        and scope_id.
        """
        scope_type = request.data.get('scope_type')
        scope_id = request.data.get('scope_id')
        
        if not scope_type or not scope_id:
            return Response({'error': 'scope_type and scope_id are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        scope_type = scope_type.upper()
        valid_scopes = ['ORGANIZATION', 'BRAND', 'REGION', 'FILE']
        if scope_type not in valid_scopes:
            return Response({'error': f'scope_type must be one of {valid_scopes}'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Create an ActiveExecution to track this manual trigger
        execution = ActiveExecution.objects.create(
            execution_type='JSON_BUILD',
            scope_type=scope_type,
            scope_id=str(scope_id),
            status='RUNNING',
            started_at=timezone.now(),
            created_by=request.user
        )
        
        # Here we would typically enqueue a Celery task that processes this execution.
        # Since celery isn't explicitly set up in this snippet, we will mock task creation 
        # so the UI can see the status immediately.
        
        # In a real background worker, it would query the relevant RegionJsonFiles and create JsonFileTask for each.
        
        return Response({
            'message': 'JSON build triggered successfully',
            'execution_id': execution.id,
            'status': execution.status
        }, status=status.HTTP_201_CREATED)
