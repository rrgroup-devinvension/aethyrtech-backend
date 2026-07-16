from rest_framework import serializers
from shared.base.serializers import BaseModelSerializer
from .models import (
    Scheduler,
    ActiveExecution,
    ExecutionHistory,
    DataDumpTask,
    JsonFileTask,
    TaskHistory
)

class SchedulerSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = Scheduler
        fields = ('id', 'created_at', 'updated_at') + (
            'name', 'type', 'cron', 'configuration', 'status', 'last_run', 'next_run'
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ('last_run', 'next_run')

class ActiveExecutionSerializer(BaseModelSerializer):
    scheduler_name = serializers.CharField(source='scheduler.name', read_only=True, allow_null=True)
    
    class Meta(BaseModelSerializer.Meta):
        model = ActiveExecution
        fields = ('id', 'created_at', 'updated_at') + (
            'scheduler', 'scheduler_name', 'execution_type', 'scope_type',
            'configuration', 'status', 'total_tasks', 'completed_tasks',
            'failed_tasks', 'celery_group_id', 'created_by', 'started_at', 'completed_at'
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ('scheduler_name',)

class ExecutionHistorySerializer(BaseModelSerializer):
    scheduler_name = serializers.CharField(source='scheduler.name', read_only=True, allow_null=True)
    
    class Meta(BaseModelSerializer.Meta):
        model = ExecutionHistory
        fields = ('id', 'created_at', 'updated_at') + (
            'scheduler', 'scheduler_name', 'execution_type', 'scope_type',
            'configuration', 'status', 'total_tasks', 'completed_tasks',
            'failed_tasks', 'celery_group_id', 'created_by', 'started_at', 'completed_at'
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ('scheduler_name',)

class DataDumpTaskSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = DataDumpTask
        fields = ('id', 'created_at', 'updated_at') + (
            'execution', 'api_dump_id', 'metadata', 'status', 'retry_count',
            'error_message', 'celery_task_id', 'started_at', 'completed_at'
        )

class JsonFileTaskSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = JsonFileTask
        fields = ('id', 'created_at', 'updated_at') + (
            'execution', 'region_json_id', 'metadata', 'status', 'retry_count',
            'error_message', 'celery_task_id', 'started_at', 'completed_at'
        )

class TaskHistorySerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = TaskHistory
        fields = ('id', 'created_at', 'updated_at') + (
            'execution', 'task_type', 'resource_id', 'resource_metadata', 'status', 'retry_count',
            'error_message', 'celery_task_id', 'started_at', 'completed_at'
        )
