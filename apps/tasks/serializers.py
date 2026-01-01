from rest_framework import serializers
from apps.scheduler.models import Task, Scheduler, SchedulerJob


class JsonFileSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    filename = serializers.CharField()
    file_path = serializers.CharField(allow_null=True, required=False)
    last_updated = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    error_message = serializers.CharField(allow_null=True, required=False)


class BrandJsonSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    brand_name = serializers.CharField()
    last_updated = serializers.DateTimeField(allow_null=True)
    status = serializers.CharField()
    files = JsonFileSerializer(many=True)


class SchedulerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scheduler
        fields = ('id', 'name', 'type', 'trigger_type', 'cron_expression', 'status', 'last_run_at', 'next_run_at', 'created_at')


class SchedulerJobSerializer(serializers.ModelSerializer):
    scheduler = SchedulerSerializer(read_only=True)

    class Meta:
        model = SchedulerJob
        fields = ('id', 'scheduler', 'triggered_by', 'scope_type', 'scope_id', 'task_group', 'status', 'started_at', 'ended_at', 'created_at')


class TaskSerializer(serializers.ModelSerializer):
    scheduler_job = SchedulerJobSerializer(read_only=True)

    class Meta:
        model = Task
        fields = ('id', 'scheduler_job', 'task_type', 'entity_type', 'entity_id', 'entity_name', 'status', 'started_at', 'ended_at', 'error_message', 'extra_context', 'created_at')
