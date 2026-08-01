from typing import ClassVar

from django.db import models

from shared.base.models import BaseModel


class Scheduler(BaseModel):
    """Model representing a scheduled job for executing data dumps or JSON builds."""
    SCHEDULER_TYPES: ClassVar[tuple] = (('DATA_DUMP', 'Data Dump'), ('JSON_BUILD', 'Json Build'))

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=SCHEDULER_TYPES, blank=True, default='')
    cron = models.CharField(max_length=100, blank=True, default='')
    configuration = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Active')
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    retry_count = models.IntegerField(default=3)
    retry_delay_seconds = models.IntegerField(default=300)
    timeout_seconds = models.IntegerField(default=3600)
    concurrency_policy = models.CharField(
        max_length=50,
        choices=[('ALLOW', 'Allow'), ('SKIP', 'Skip'), ('REPLACE', 'Replace')],
        default='SKIP'
    )
    notify_emails = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'schedulers'

class BaseExecution(BaseModel):
    """Abstract base model defining shared fields for tracking active and historical execution runs."""
    EXECUTION_TYPES: ClassVar[tuple] = (('DATA_DUMP', 'Data Dump'), ('JSON_BUILD', 'Json Build'))
    SCOPE_TYPES: ClassVar[tuple] = (
        ('CATEGORY', 'Category'),
        ('KEYWORD', 'Keyword'),
        ('LOCATION', 'Location'),
        ('REGION', 'Region')
    )
    STATUS_CHOICES: ClassVar[tuple] = (
        ('PENDING', 'Pending'), ('RUNNING', 'Running'), ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'), ('STOPPED', 'Stopped')
    )

    scheduler = models.ForeignKey(Scheduler, on_delete=models.SET_NULL, null=True, blank=True)
    execution_type = models.CharField(max_length=50, choices=EXECUTION_TYPES, blank=True, default='')
    scope_type = models.CharField(max_length=50, choices=SCOPE_TYPES, blank=True, default='')
    scope_id = models.CharField(max_length=255, blank=True, default='')
    scope_name = models.CharField(max_length=255, blank=True, default='')
    configuration = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, blank=True, default='')
    total_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    failed_tasks = models.IntegerField(default=0)
    stopped_tasks = models.IntegerField(default=0)
    celery_group_id = models.CharField(max_length=255, blank=True, default='')
    created_by = models.ForeignKey('core_users.User', on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class ActiveExecution(BaseExecution):
    """Model representing an execution job that is currently active or recently processed."""
    class Meta:
        db_table = 'active_executions'


class ExecutionHistory(BaseExecution):
    """Model for archiving completed, failed, or stopped execution jobs."""
    class Meta:
        db_table = 'execution_history'


class BaseTask(BaseModel):
    """Abstract base model for tracking individual tasks within an execution."""
    status = models.CharField(max_length=50, blank=True, default='')
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    celery_task_id = models.CharField(max_length=255, blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class DataDumpTask(BaseTask):
    """Model representing an individual active data dump task."""
    execution = models.ForeignKey(ActiveExecution, on_delete=models.CASCADE)
    api_dump_id = models.CharField(max_length=255, blank=True, default='')
    metadata = models.JSONField(null=True, blank=True, help_text="Stores keyword, location, or region_json IDs")

    class Meta:
        db_table = 'data_dump_tasks'
        indexes = (
            models.Index(fields=['execution', 'status'], name='idx_datadump_exec_status'),
        )


class JsonFileTask(BaseTask):
    """Model representing an individual active JSON generation task."""
    execution = models.ForeignKey(ActiveExecution, on_delete=models.CASCADE)
    region_json_id = models.CharField(max_length=255, blank=True, default='')
    metadata = models.JSONField(null=True, blank=True, help_text="Stores keyword, location, or region_json IDs")

    class Meta:
        db_table = 'json_file_tasks'
        indexes = (
            models.Index(fields=['execution', 'status'], name='idx_jsonfile_exec_status'),
        )

class TaskHistory(BaseTask):
    """Model for archiving completed, failed, or stopped tasks."""
    TASK_TYPES: ClassVar[tuple] = (
        ('DATA_DUMP', 'Data Dump'),
        ('JSON_BUILD', 'Json Build')
    )

    # Links to the historical execution
    execution = models.ForeignKey(ExecutionHistory, on_delete=models.CASCADE, related_name='historical_tasks')
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)

    # Store a primary ID here (e.g., the region_json ID, or a concatenated string like 'kw:1-loc:2')
    resource_id = models.CharField(max_length=255, blank=True, default='')

    # BEST PRACTICE: Store the exact IDs so you don't lose the link to Keyword/Location
    # e.g., {"keyword_id": 5, "location_id": 12}
    resource_metadata = models.JSONField(
        null=True, blank=True, help_text="Stores keyword, location, or region_json IDs"
    )

    class Meta:
        db_table = 'task_history'
        indexes = (
            models.Index(fields=['execution', 'task_type'], name='idx_taskhist_exec_type'),
            models.Index(fields=['celery_task_id'], name='idx_taskhist_celery_id'),
        )
