import logging
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from shared.base.views import BaseViewSet
from .models import (
    Scheduler, ActiveExecution, ExecutionHistory,
    DataDumpTask, JsonFileTask, TaskHistory
)
from .serializers import (
    SchedulerSerializer, ActiveExecutionSerializer, ExecutionHistorySerializer,
    DataDumpTaskSerializer, JsonFileTaskSerializer, TaskHistorySerializer
)
from .services import ExecutionManager

logger = logging.getLogger(__name__)

@extend_schema_view(
    list=extend_schema(summary="List Schedulers"),
    retrieve=extend_schema(summary="Get Scheduler"),
    create=extend_schema(summary="Create Scheduler"),
    update=extend_schema(summary="Update Scheduler"),
    partial_update=extend_schema(summary="Partial Update Scheduler"),
    destroy=extend_schema(summary="Delete Scheduler")
)
class SchedulerViewSet(BaseViewSet):
    queryset = Scheduler.objects.all().order_by('-created_at')
    serializer_class = SchedulerSerializer
    search_fields = ('name', 'type', 'status')
    ordering_fields = ('name', 'created_at', 'updated_at', 'last_run', 'next_run')

    @extend_schema(summary="Manually trigger a scheduler")
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        scheduler = self.get_object()
        logger.info(f"Manual run triggered for scheduler: {scheduler.id}")
        
        try:
            execution = ExecutionManager.create_execution_from_scheduler(
                scheduler=scheduler,
                user=request.user
            )
            return Response({
                'message': 'Execution started successfully',
                'execution_id': execution.id,
                'status': execution.status
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to start execution: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Set status of a scheduler")
    @action(detail=True, methods=['post'], url_path='set-status')
    def set_status(self, request, pk=None, **kwargs):
        scheduler = self.get_object()
        new_status = request.data.get('status')
        if not new_status or new_status not in ['Active', 'Inactive']:
            return Response({'error': 'Invalid status provided. Must be Active or Inactive.'}, status=status.HTTP_400_BAD_REQUEST)
        
        scheduler.status = new_status
        scheduler.save(update_fields=['status'])
        
        return Response({
            'message': 'Status updated successfully',
            'status': scheduler.status
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List Active Executions"),
    retrieve=extend_schema(summary="Get Active Execution"),
    create=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(summary="Delete Active Execution")
)
class ActiveExecutionViewSet(BaseViewSet):
    queryset = ActiveExecution.objects.all().select_related('scheduler', 'created_by').order_by('-created_at')
    serializer_class = ActiveExecutionSerializer
    search_fields = ('execution_type', 'status', 'scheduler__name')
    ordering_fields = ('created_at', 'started_at', 'completed_at', 'status')

    @extend_schema(summary="Stop a running execution")
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        execution = self.get_object()
        if execution.status != 'RUNNING':
            return Response({
                'error': f'Execution is not running. Current status: {execution.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        stopped_execution = ExecutionManager.stop_execution(execution)
        serializer = self.get_serializer(stopped_execution)
        return Response({
            'message': 'Execution stopped successfully',
            'execution': serializer.data
        }, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary="List Execution History"),
    retrieve=extend_schema(summary="Get Execution History Detail"),
    create=extend_schema(exclude=True),
    update=extend_schema(exclude=True),
    partial_update=extend_schema(exclude=True),
    destroy=extend_schema(exclude=True)
)
class ExecutionHistoryViewSet(BaseViewSet):
    queryset = ExecutionHistory.objects.all().select_related('scheduler', 'created_by').order_by('-created_at')
    serializer_class = ExecutionHistorySerializer
    search_fields = ('execution_type', 'status', 'scheduler__name')
    ordering_fields = ('created_at', 'started_at', 'completed_at')


class DataDumpTaskViewSet(BaseViewSet):
    queryset = DataDumpTask.objects.all().select_related('execution').order_by('-created_at')
    serializer_class = DataDumpTaskSerializer
    search_fields = ('status', 'api_dump_id', 'celery_task_id')
    ordering_fields = ('created_at', 'started_at', 'completed_at', 'status')
    filterset_fields = ['execution', 'status']


class JsonFileTaskViewSet(BaseViewSet):
    queryset = JsonFileTask.objects.all().select_related('execution').order_by('-created_at')
    serializer_class = JsonFileTaskSerializer
    search_fields = ('status', 'region_json_id', 'celery_task_id')
    ordering_fields = ('created_at', 'started_at', 'completed_at', 'status')
    filterset_fields = ['execution', 'status']


class TaskHistoryViewSet(BaseViewSet):
    queryset = TaskHistory.objects.all().select_related('execution').order_by('-created_at')
    serializer_class = TaskHistorySerializer
    search_fields = ('status', 'task_type', 'resource_id', 'celery_task_id')
    ordering_fields = ('created_at', 'started_at', 'completed_at', 'status')
    filterset_fields = ['execution', 'status', 'task_type']
