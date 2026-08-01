from rest_framework import serializers

from shared.base.serializers import BaseModelSerializer

from .models import ActiveExecution, DataDumpTask, ExecutionHistory, JsonFileTask, Scheduler, TaskHistory


class SchedulerSerializer(BaseModelSerializer):
    """Serializer for mapping Scheduler model instances to JSON representations."""
    class Meta(BaseModelSerializer.Meta):
        model = Scheduler
        fields = (
            'id', 'created_at', 'updated_at',
            'name', 'type', 'cron', 'configuration', 'status', 'last_run', 'next_run',
            'timezone', 'retry_count', 'retry_delay_seconds', 'timeout_seconds',
            'concurrency_policy', 'notify_emails'
        )
        read_only_fields = (*BaseModelSerializer.Meta.read_only_fields, 'last_run', 'next_run')

class ActiveExecutionSerializer(BaseModelSerializer):
    """Serializer for mapping ActiveExecution model instances to JSON representations."""
    scheduler_name = serializers.CharField(source='scheduler.name', read_only=True, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = ActiveExecution
        fields = (
            'id', 'created_at', 'updated_at',
            'scheduler', 'scheduler_name', 'execution_type', 'scope_type', 'scope_id', 'scope_name',
            'configuration', 'status', 'total_tasks', 'completed_tasks',
            'failed_tasks', 'stopped_tasks', 'celery_group_id', 'created_by', 'started_at', 'completed_at'
        )
        read_only_fields = (*BaseModelSerializer.Meta.read_only_fields, 'scheduler_name')

class ExecutionHistorySerializer(BaseModelSerializer):
    """Serializer for mapping ExecutionHistory model instances to JSON representations."""
    scheduler_name = serializers.CharField(source='scheduler.name', read_only=True, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = ExecutionHistory
        fields = (
            'id', 'created_at', 'updated_at',
            'scheduler', 'scheduler_name', 'execution_type', 'scope_type', 'scope_id', 'scope_name',
            'configuration', 'status', 'total_tasks', 'completed_tasks',
            'failed_tasks', 'stopped_tasks', 'celery_group_id', 'created_by', 'started_at', 'completed_at'
        )
        read_only_fields = (*BaseModelSerializer.Meta.read_only_fields, 'scheduler_name')

class DataDumpTaskSerializer(BaseModelSerializer):
    """Serializer for mapping DataDumpTask model instances to JSON representations."""
    task_type = serializers.CharField(default='DATA_DUMP', read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = DataDumpTask
        fields = (
            'id', 'created_at', 'updated_at',
            'execution', 'api_dump_id', 'metadata', 'status', 'retry_count',
            'error_message', 'celery_task_id', 'started_at', 'completed_at', 'task_type'
        )

class JsonFileTaskSerializer(BaseModelSerializer):
    """Serializer for mapping JsonFileTask model instances to JSON representations."""
    task_type = serializers.CharField(default='JSON_BUILD', read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = JsonFileTask
        fields = (
            'id', 'created_at', 'updated_at',
            'execution', 'region_json_id', 'metadata', 'status', 'retry_count',
            'error_message', 'celery_task_id', 'started_at', 'completed_at', 'task_type'
        )

class TaskHistorySerializer(BaseModelSerializer):
    """Serializer for mapping TaskHistory model instances to JSON representations."""
    class Meta(BaseModelSerializer.Meta):
        model = TaskHistory
        fields = (
            'id', 'created_at', 'updated_at',
            'execution', 'task_type', 'resource_id', 'resource_metadata', 'status', 'retry_count',
            'error_message', 'celery_task_id', 'started_at', 'completed_at'
        )
