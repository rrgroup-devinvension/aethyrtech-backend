"""
Serializers for scheduler models.
"""
from rest_framework import serializers
from apps.scheduler.models import (
    Scheduler,
    SchedulerJob,
    Task,
    KeywordPincode,
    BrandJsonFile
)
from apps.category.models import Category, CategoryKeyword, CategoryPincode


class SchedulerSerializer(serializers.ModelSerializer):
    """Serializer for Scheduler model."""
    last_job = serializers.SerializerMethodField()
    
    class Meta:
        model = Scheduler
        fields = [
            'id', 'name', 'type', 'trigger_type', 'cron_expression',
            'status', 'last_run_at', 'next_run_at', 'last_job', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_run_at', 'next_run_at', 'created_at', 'updated_at']

    def get_last_job(self, obj):
        """Return a brief representation of the scheduler's latest job (if any)."""
        job = SchedulerJob.objects.filter(scheduler=obj).order_by('-created_at').first()
        if not job:
            return None

        # Prepare brief data
        tasks = job.tasks.all()
        return {
            'id': job.id,
            'status': job.status,
            'task_group': job.task_group,
            'started_at': job.started_at,
            'ended_at': job.ended_at,
            'tasks': {
                'total': tasks.count(),
                'success': tasks.filter(status=Task.TaskStatus.SUCCESS).count(),
                'failed': tasks.filter(status=Task.TaskStatus.FAILED).count(),
                'running': tasks.filter(status=Task.TaskStatus.RUNNING).count(),
                'pending': tasks.filter(status=Task.TaskStatus.PENDING).count(),
            }
        }


class SchedulerJobSerializer(serializers.ModelSerializer):
    """Serializer for SchedulerJob model."""
    scheduler_name = serializers.CharField(source='scheduler.name', read_only=True, allow_null=True)
    
    # Task statistics
    total_tasks = serializers.SerializerMethodField()
    pending_tasks = serializers.SerializerMethodField()
    running_tasks = serializers.SerializerMethodField()
    success_tasks = serializers.SerializerMethodField()
    failed_tasks = serializers.SerializerMethodField()
    stopped_tasks = serializers.SerializerMethodField()

    # Lists of succeeded/failed tasks for expanded view
    success_list = serializers.SerializerMethodField()
    failed_list = serializers.SerializerMethodField()
    
    class Meta:
        model = SchedulerJob
        fields = [
            'id', 'scheduler', 'scheduler_name', 'triggered_by', 'scope_type',
            'scope_id', 'task_group', 'status', 'started_at', 'ended_at',
            'total_tasks', 'pending_tasks', 'running_tasks', 'success_tasks', 'failed_tasks', 'stopped_tasks',
            'success_list', 'failed_list', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'scheduler_name', 'total_tasks', 'pending_tasks', 'running_tasks', 'success_tasks', 'failed_tasks', 'stopped_tasks', 'success_list', 'failed_list', 'created_at', 'updated_at']

    def _task_qs(self, obj):
        return obj.tasks.all()

    def get_total_tasks(self, obj):
        return self._task_qs(obj).count()

    def get_pending_tasks(self, obj):
        return self._task_qs(obj).filter(status=Task.TaskStatus.PENDING).count()

    def get_running_tasks(self, obj):
        return self._task_qs(obj).filter(status=Task.TaskStatus.RUNNING).count()

    def get_success_tasks(self, obj):
        return self._task_qs(obj).filter(status=Task.TaskStatus.SUCCESS).count()

    def get_failed_tasks(self, obj):
        return self._task_qs(obj).filter(status=Task.TaskStatus.FAILED).count()
    
    def get_stopped_tasks(self, obj):
        return self._task_qs(obj).filter(status=Task.TaskStatus.STOPPED).count()

    def _serialize_task_brief(self, task):
        return {
            'id': task.id,
            'task_type': task.task_type,
            'entity_type': task.entity_type,
            'entity_id': task.entity_id,
            'entity_name': task.entity_name,
            'error_message': task.error_message,
            'started_at': task.started_at,
            'ended_at': task.ended_at,
        }

    def get_success_list(self, obj):
        qs = self._task_qs(obj).filter(status=Task.TaskStatus.SUCCESS)
        return [self._serialize_task_brief(t) for t in qs]

    def get_failed_list(self, obj):
        qs = self._task_qs(obj).filter(status=Task.TaskStatus.FAILED)
        return [self._serialize_task_brief(t) for t in qs]


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""
    scheduler_job_id = serializers.IntegerField(source='scheduler_job.id', read_only=True, allow_null=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = [
            'id', 'scheduler_job', 'scheduler_job_id', 'task_type', 'entity_type',
            'entity_id', 'entity_name', 'extra_context', 'status',
            'started_at', 'ended_at', 'duration_seconds', 'error_message',
            'retry_of_task', 'celery_task_id', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'scheduler_job_id', 'duration_seconds', 'created_at', 'updated_at']
    
    def get_duration_seconds(self, obj):
        """Calculate task duration in seconds."""
        if obj.started_at and obj.ended_at:
            return (obj.ended_at - obj.started_at).total_seconds()
        return None
