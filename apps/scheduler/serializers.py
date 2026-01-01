from rest_framework import serializers
from apps.scheduler.models import (
    Scheduler,
    SchedulerJob,
    Task,
    Pincode,
    Keyword,
    BrandJsonFile
)


class PincodeSerializer(serializers.ModelSerializer):
    """Serializer for Pincode model."""
    
    class Meta:
        model = Pincode
        fields = ['id', 'pincode', 'city', 'state', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class KeywordSerializer(serializers.ModelSerializer):
    """Serializer for Keyword model."""
    pincode_value = serializers.CharField(source='pincode.pincode', read_only=True)
    last_running_task_id = serializers.IntegerField(source='last_running_task.id', read_only=True, allow_null=True)
    last_completed_task_id = serializers.IntegerField(source='last_completed_task.id', read_only=True, allow_null=True)
    
    class Meta:
        model = Keyword
        fields = [
            'id', 'keyword', 'pincode', 'pincode_value',
            'is_active', 'last_running_task_id', 'last_completed_task_id',
            'last_synced', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_running_task_id', 'last_completed_task_id', 'last_synced', 'error_message', 'created_at', 'updated_at']


class SchedulerSerializer(serializers.ModelSerializer):
    """Serializer for Scheduler model."""
    
    class Meta:
        model = Scheduler
        fields = [
            'id', 'name', 'type', 'trigger_type', 'cron_expression',
            'status', 'last_run_at', 'next_run_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_run_at', 'next_run_at', 'created_at', 'updated_at']


class SchedulerJobSerializer(serializers.ModelSerializer):
    """Serializer for SchedulerJob model."""
    scheduler_name = serializers.CharField(source='scheduler.name', read_only=True, allow_null=True)
    
    class Meta:
        model = SchedulerJob
        fields = [
            'id', 'scheduler', 'scheduler_name', 'triggered_by', 'scope_type',
            'scope_id', 'task_group', 'status', 'started_at', 'ended_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'scheduler_name', 'created_at', 'updated_at']


class TaskSerializer(serializers.ModelSerializer):
    """Serializer for Task model."""
    
    class Meta:
        model = Task
        fields = [
            'id', 'scheduler_job', 'task_type', 'entity_type', 'entity_id',
            'entity_name', 'extra_context', 'status', 'started_at', 'ended_at',
            'error_message', 'retry_of_task', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BrandJsonFileSerializer(serializers.ModelSerializer):
    """Serializer for BrandJsonFile model."""
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    last_running_task_id = serializers.IntegerField(source='last_running_task.id', read_only=True, allow_null=True)
    last_completed_task_id = serializers.IntegerField(source='last_completed_task.id', read_only=True, allow_null=True)
    
    class Meta:
        model = BrandJsonFile
        fields = [
            'id', 'brand', 'brand_name', 'template', 'filename', 'file_path',
            'last_running_task_id', 'last_completed_task_id',
            'last_synced', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'brand_name', 'last_running_task_id', 'last_completed_task_id', 'created_at', 'updated_at']
