from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from core.permissions import IsStaffOrReadOnly
from django.conf import settings
from django.utils import timezone

from apps.scheduler.models import Task, Scheduler, SchedulerJob, BrandJsonFile, Keyword
from apps.scheduler import services, tasks as scheduler_tasks
from apps.scheduler.service_layer import stop_task as service_stop_task
from apps.tasks.serializers import BrandJsonSerializer, JsonFileSerializer, SchedulerSerializer, SchedulerJobSerializer, TaskSerializer
from apps.brand.models import Brand
from core.views import BaseViewSet
from django.db.models import Q, Count
from django.db.models import Q, Count


class JsonsListView(APIView):
    """List all brands with JSON build status and files."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):
        brands = Brand.objects.filter(is_deleted=False)
        json_templates = getattr(settings, 'SCHEDULER_JSON_TEMPLATES', [])
        result = []
        
        for b in brands:
            # Use BrandJsonFile table as source of truth for files
            files_qs = BrandJsonFile.objects.filter(brand=b)
            files = []
            template_status = {}
            for fobj in files_qs:
                tpl = fobj.template
                # find latest task for this brand/template to get status
                latest_task = Task.objects.filter(entity_type=Task.EntityType.JSON_FILE, entity_id=b.id).filter(
                    extra_context__template=tpl
                ).order_by('-created_at').first()

                status_val = latest_task.status if latest_task else 'PENDING'
                last_updated = latest_task.ended_at if latest_task and latest_task.ended_at else fobj.last_synced or b.updated_at

                if tpl not in template_status:
                    template_status[tpl] = status_val

                files.append({
                    'id': fobj.id,
                    'filename': fobj.filename,
                    'file_path': fobj.file_path,
                    'template': tpl,
                    'last_updated': last_updated,
                    'status': status_val,
                    'error_message': fobj.error_message,
                })
            
            # Determine overall brand status from templates
            if template_status:
                if any(s == Task.TaskStatus.FAILED for s in template_status.values()):
                    status_val = 'FAILED'
                elif any(s == Task.TaskStatus.RUNNING for s in template_status.values()):
                    status_val = 'RUNNING'
                elif all(s == Task.TaskStatus.SUCCESS for s in template_status.values()):
                    status_val = 'SUCCESS'
                else:
                    status_val = 'PENDING'
            else:
                status_val = 'PENDING'
            
            last_task = Task.objects.filter(entity_type=Task.EntityType.JSON_FILE, entity_id=b.id).order_by('-created_at').first()
            last_updated = last_task.ended_at if last_task and last_task.ended_at else b.updated_at

            result.append({
                'id': b.id,
                'brand_name': b.name,
                'last_updated': last_updated,
                'status': status_val,
                'json_templates': json_templates,
                'files': files[:20],  # limit to recent 20
            })

        # Return plain dict, let StandardJSONRenderer wrap it
        return Response(result, status=status.HTTP_200_OK)


class BrandFilesView(APIView):
    """Get files for a specific brand."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request, brand_id: int):
        files = []
        for fobj in BrandJsonFile.objects.filter(brand_id=brand_id):
            tpl = fobj.template
            latest_task = Task.objects.filter(entity_type=Task.EntityType.JSON_FILE, entity_id=brand_id).filter(
                extra_context__template=tpl
            ).order_by('-created_at').first()
            status_val = latest_task.status if latest_task else 'PENDING'
            last_updated = latest_task.ended_at if latest_task and latest_task.ended_at else fobj.last_synced or None
            files.append({
                'id': fobj.id,
                'filename': fobj.filename,
                'file_path': fobj.file_path,
                'template': tpl,
                'last_updated': last_updated,
                'status': status_val,
                'error_message': fobj.error_message,
            })

        return Response(files, status=status.HTTP_200_OK)


class BrandSyncView(APIView):
    """Sync JSON files for a specific brand."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def post(self, request, brand_id: int):
        job = services.create_scheduler_job(scheduler_id=None, triggered_by='ADMIN', scope_type='BRAND', scope_id=brand_id, task_group='JSON_BUILD')
        return Response({'detail': 'Job created', 'job_id': job.id}, status=status.HTTP_201_CREATED)


class FileSyncView(APIView):
    """Sync a specific JSON file (retry)."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def post(self, request, file_id: int):
        # file_id is BrandJsonFile.id; find the template and brand to create a task
        from apps.scheduler.models import BrandJsonFile
        try:
            file_obj = BrandJsonFile.objects.get(id=file_id)
        except BrandJsonFile.DoesNotExist:
            return Response({'detail': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Create a job with BRAND scope for this specific brand, but only for this template
        # We'll create a single-task job by creating the job and manually creating one task
        job = SchedulerJob.objects.create(
            triggered_by='ADMIN',
            scope_type=SchedulerJob.ScopeType.BRAND,
            scope_id=file_obj.brand_id,
            task_group=SchedulerJob.TaskGroup.JSON_BUILD,
            status=SchedulerJob.JobStatus.RUNNING,
            started_at=timezone.now()
        )
        
        # Create single task for this template only
        t = Task.objects.create(
            scheduler_job=job,
            task_type=Task.TaskType.JSON_BUILD,
            entity_type=Task.EntityType.JSON_FILE,
            entity_id=file_obj.brand_id,
            entity_name=file_obj.template,
            extra_context={'template': file_obj.template, 'brand_id': file_obj.brand_id},
            status=Task.TaskStatus.PENDING,
        )
        
        # Dispatch task to celery
        from apps.scheduler.tasks import run_task
        run_task.apply_async((t.id,))
        
        return Response({'detail': 'Job created', 'job_id': job.id}, status=status.HTTP_201_CREATED)


class JsonSyncAllView(APIView):
    """Sync all brands (global sync)."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def post(self, request):
        job = services.create_scheduler_job(scheduler_id=None, triggered_by='ADMIN', scope_type='GLOBAL', scope_id=None, task_group='JSON_BUILD')
        return Response({'detail': 'Job created', 'job_id': job.id}, status=status.HTTP_201_CREATED)


class JsonJobStatusView(APIView):
    """Get status of the latest JSON builder job."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):
        # Find the most recent global or brand-level JSON_BUILD job
        latest_job = SchedulerJob.objects.filter(
            task_group__in=[SchedulerJob.TaskGroup.JSON_BUILD, SchedulerJob.TaskGroup.BOTH]
        ).order_by('-created_at').first()
        
        if not latest_job:
            return Response({
                'is_running': False,
                'job': None
            }, status=status.HTTP_200_OK)
        
        # Get task stats
        tasks = latest_job.tasks.all()
        total = tasks.count()
        success = tasks.filter(status=Task.TaskStatus.SUCCESS).count()
        failed = tasks.filter(status=Task.TaskStatus.FAILED).count()
        running = tasks.filter(status=Task.TaskStatus.RUNNING).count()
        pending = tasks.filter(status=Task.TaskStatus.PENDING).count()
        
        duration = None
        if latest_job.started_at and latest_job.ended_at:
            duration = (latest_job.ended_at - latest_job.started_at).total_seconds()
        
        return Response({
            'is_running': latest_job.status == SchedulerJob.JobStatus.RUNNING,
            'job': {
                'id': latest_job.id,
                'status': latest_job.status,
                'scope_type': latest_job.scope_type,
                'scope_id': latest_job.scope_id,
                'started_at': latest_job.started_at,
                'ended_at': latest_job.ended_at,
                'duration_seconds': duration,
                'tasks': {
                    'total': total,
                    'success': success,
                    'failed': failed,
                    'running': running,
                    'pending': pending
                }
            }
        }, status=status.HTTP_200_OK)


class SchedulerViewSet(BaseViewSet):
    """CRUD operations for Scheduler."""
    queryset = Scheduler.objects.all()
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    serializer_class = SchedulerSerializer

    @action(detail=True, methods=['post'])
    def trigger(self, request, pk=None):
        """Manually trigger a scheduler."""
        scheduler = self.get_object()
        job = services.create_scheduler_job(scheduler_id=scheduler.id, triggered_by='ADMIN', scope_type='GLOBAL', scope_id=None, task_group='BOTH')
        return Response({'detail': 'Job created', 'job_id': job.id}, status=status.HTTP_201_CREATED)
    
    def perform_create(self, serializer):
        obj = serializer.save()
        # if cron-based, sync periodic task
        try:
            services.sync_periodic_task_for_scheduler(obj)
        except Exception:
            pass

    def perform_update(self, serializer):
        obj = serializer.save()
        try:
            services.sync_periodic_task_for_scheduler(obj)
        except Exception:
            pass

    def perform_destroy(self, instance):
        try:
            services.remove_periodic_task_for_scheduler(instance)
        except Exception:
            pass
        instance.delete()


class SchedulerJobViewSet(BaseViewSet):
    """List and manage SchedulerJobs."""
    queryset = SchedulerJob.objects.all()
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    serializer_class = SchedulerJobSerializer

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed job."""
        job = self.get_object()
        scheduler_tasks.process_scheduler_job.apply_async((job.id,))
        return Response({'detail': 'Job retriggered'}, status=status.HTTP_200_OK)


class TaskViewSet(BaseViewSet):
    """List and manage Tasks."""
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]
    serializer_class = TaskSerializer

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed task."""
        t = self.get_object()
        # create retry task
        retry_task = Task.objects.create(
            scheduler_job=t.scheduler_job,
            task_type=t.task_type,
            entity_type=t.entity_type,
            entity_id=t.entity_id,
            entity_name=t.entity_name,
            extra_context=t.extra_context,
            status=Task.TaskStatus.PENDING,
            retry_of_task=t
        )
        scheduler_tasks.run_task.apply_async((retry_task.id,))
        return Response({'detail': 'Task retried', 'task_id': retry_task.id}, status=status.HTTP_201_CREATED)


class SchedulerJobListView(APIView):
    """List all scheduler jobs with filtering and pagination."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):
        # Get query parameters for filtering
        status_filter = request.query_params.get('status', None)
        triggered_by = request.query_params.get('triggered_by', None)
        scope_type = request.query_params.get('scope_type', None)
        task_group = request.query_params.get('task_group', None)
        
        # Build query
        jobs = SchedulerJob.objects.select_related('scheduler').annotate(
            total_tasks=Count('tasks'),
            success_tasks=Count('tasks', filter=Q(tasks__status=Task.TaskStatus.SUCCESS)),
            failed_tasks=Count('tasks', filter=Q(tasks__status=Task.TaskStatus.FAILED)),
            running_tasks=Count('tasks', filter=Q(tasks__status=Task.TaskStatus.RUNNING)),
            pending_tasks=Count('tasks', filter=Q(tasks__status=Task.TaskStatus.PENDING))
        ).order_by('-created_at')
        
        # Apply filters
        if status_filter:
            jobs = jobs.filter(status=status_filter)
        if triggered_by:
            jobs = jobs.filter(triggered_by=triggered_by)
        if scope_type:
            jobs = jobs.filter(scope_type=scope_type)
        if task_group:
            jobs = jobs.filter(task_group=task_group)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = jobs.count()
        jobs_page = jobs[start:end]
        
        result = []
        for job in jobs_page:
            result.append({
                'id': job.id,
                'scheduler_id': job.scheduler.id if job.scheduler else None,
                'scheduler_name': job.scheduler.name if job.scheduler else None,
                'triggered_by': job.triggered_by,
                'scope_type': job.scope_type,
                'scope_id': job.scope_id,
                'task_group': job.task_group,
                'status': job.status,
                'started_at': job.started_at,
                'ended_at': job.ended_at,
                'created_at': job.created_at,
                'updated_at': job.updated_at,
                'total_tasks': job.total_tasks,
                'success_tasks': job.success_tasks,
                'failed_tasks': job.failed_tasks,
                'running_tasks': job.running_tasks,
                'pending_tasks': job.pending_tasks,
            })
        
        return Response(result)


class StopSchedulerJobView(APIView):
    """Stop a running scheduler job."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def post(self, request, job_id):
        try:
            job = SchedulerJob.objects.get(id=job_id)
        except SchedulerJob.DoesNotExist:
            return Response({'error': 'Job not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if job.status != SchedulerJob.JobStatus.RUNNING:
            return Response(
                {'error': f'Job is not running. Current status: {job.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update job status to FAILED (stopped)
        job.status = SchedulerJob.JobStatus.FAILED
        job.ended_at = timezone.now()
        job.save()
        
        # Update all pending/running tasks to FAILED
        Task.objects.filter(
            scheduler_job=job,
            status__in=[Task.TaskStatus.PENDING, Task.TaskStatus.RUNNING]
        ).update(
            status=Task.TaskStatus.FAILED,
            error_message='Job stopped by user',
            ended_at=timezone.now()
        )
        
        return Response({
            'message': 'Job stopped successfully',
            'job_id': job.id,
            'status': job.status
        })


class TaskListView(APIView):
    """List all tasks with filtering and pagination."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):
        # Get query parameters for filtering
        task_type = request.query_params.get('task_type', None)
        entity_type = request.query_params.get('entity_type', None)
        status_filter = request.query_params.get('status', None)
        job_id = request.query_params.get('job_id', None)
        
        # Build query
        tasks = Task.objects.select_related('scheduler_job', 'scheduler_job__scheduler').order_by('-created_at')
        
        # Apply filters
        if task_type:
            tasks = tasks.filter(task_type=task_type)
        if entity_type:
            tasks = tasks.filter(entity_type=entity_type)
        if status_filter:
            tasks = tasks.filter(status=status_filter)
        if job_id:
            tasks = tasks.filter(scheduler_job_id=job_id)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        start = (page - 1) * page_size
        end = start + page_size
        
        total_count = tasks.count()
        tasks_page = tasks[start:end]
        
        result = []
        for task in tasks_page:
            result.append({
                'id': task.id,
                'job_id': task.scheduler_job.id if task.scheduler_job else None,
                'task_type': task.task_type,
                'entity_type': task.entity_type,
                'entity_id': task.entity_id,
                'entity_name': task.entity_name,
                'extra_context': task.extra_context,
                'status': task.status,
                'started_at': task.started_at,
                'ended_at': task.ended_at,
                'error_message': task.error_message,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
            })
        
        return Response(result)


# ============================================================================
# Data Dump Views (for Keywords)
# ============================================================================

class DataDumpListView(APIView):
    """List all keywords with data dump status."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):
        keywords = Keyword.objects.filter(is_deleted=False).select_related('pincode', 'last_running_task', 'last_completed_task').order_by('keyword', 'pincode')
        
        result = []
        for kw in keywords:
            # Determine status from last_completed_task or last_running_task
            status_val = 'PENDING'
            last_updated = kw.last_synced or kw.updated_at
            
            if kw.last_running_task and not kw.last_completed_task:
                status_val = 'RUNNING'
                last_updated = kw.last_running_task.started_at or last_updated
            elif kw.last_completed_task:
                status_val = kw.last_completed_task.status
                last_updated = kw.last_completed_task.ended_at or last_updated
            
            result.append({
                'id': kw.id,
                'keyword': kw.keyword,
                'pincode': kw.pincode.pincode,
                'pincode_id': kw.pincode.id,
                'city': kw.pincode.city,
                'state': kw.pincode.state,
                'is_active': kw.is_active,
                'last_updated': last_updated,
                'status': status_val,
                'error_message': kw.error_message,
                'last_running_task_id': kw.last_running_task.id if kw.last_running_task else None,
                'last_completed_task_id': kw.last_completed_task.id if kw.last_completed_task else None,
            })
        
        return Response(result, status=status.HTTP_200_OK)


class KeywordSyncAllView(APIView):
    """Sync all keywords (global sync)."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def post(self, request):
        job = services.create_scheduler_job(
            scheduler_id=None,
            triggered_by='ADMIN',
            scope_type='GLOBAL',
            scope_id=None,
            task_group='DATA_DUMP'
        )
        return Response({'detail': 'Job created', 'job_id': job.id}, status=status.HTTP_201_CREATED)


class KeywordSyncView(APIView):
    """Sync a specific keyword."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def post(self, request, keyword_id: int):
        job = services.create_scheduler_job(
            scheduler_id=None,
            triggered_by='ADMIN',
            scope_type='KEYWORD',
            scope_id=keyword_id,
            task_group='DATA_DUMP'
        )
        return Response({'detail': 'Job created', 'job_id': job.id}, status=status.HTTP_201_CREATED)


class DataDumpJobStatusView(APIView):
    """Get status of the latest data dump job."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def get(self, request):
        # Find the most recent DATA_DUMP job
        latest_job = SchedulerJob.objects.filter(
            task_group__in=[SchedulerJob.TaskGroup.DATA_DUMP, SchedulerJob.TaskGroup.BOTH]
        ).order_by('-created_at').first()
        
        if not latest_job:
            return Response({
                'is_running': False,
                'job': None
            }, status=status.HTTP_200_OK)
        
        # Get task stats
        tasks = latest_job.tasks.all()
        total = tasks.count()
        success = tasks.filter(status=Task.TaskStatus.SUCCESS).count()
        failed = tasks.filter(status=Task.TaskStatus.FAILED).count()
        running = tasks.filter(status=Task.TaskStatus.RUNNING).count()
        pending = tasks.filter(status=Task.TaskStatus.PENDING).count()
        
        duration = None
        if latest_job.started_at and latest_job.ended_at:
            duration = (latest_job.ended_at - latest_job.started_at).total_seconds()
        
        return Response({
            'is_running': latest_job.status == SchedulerJob.JobStatus.RUNNING,
            'job': {
                'id': latest_job.id,
                'status': latest_job.status,
                'scope_type': latest_job.scope_type,
                'scope_id': latest_job.scope_id,
                'started_at': latest_job.started_at,
                'ended_at': latest_job.ended_at,
                'duration_seconds': duration,
                'tasks': {
                    'total': total,
                    'success': success,
                    'failed': failed,
                    'running': running,
                    'pending': pending
                }
            }
        }, status=status.HTTP_200_OK)


class StopTaskView(APIView):
    """Stop a single running task."""
    permission_classes = [IsAuthenticated, IsStaffOrReadOnly]

    def post(self, request, task_id):
        task = service_stop_task(task_id)
        
        if not task:
            return Response({'error': 'Task not found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'message': 'Task stopped successfully',
            'task_id': task.id,
            'status': task.status
        })
