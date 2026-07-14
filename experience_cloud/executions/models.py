from django.db import models
from shared.base.models import BaseModel

class Scheduler(BaseModel):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, null=True, blank=True)
    cron = models.CharField(max_length=100, null=True, blank=True)
    configuration = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=50, default='Active')
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'schedulers'

class BaseExecution(BaseModel):
    """Abstract base class to share fields between ActiveExecutions and ExecutionHistory"""
    EXECUTION_TYPES = [('DATA_DUMP', 'Data Dump'), ('JSON_BUILD', 'Json Build')]
    SCOPE_TYPES = [('CATEGORY', 'Category'), ('KEYWORD', 'Keyword'), ('LOCATION', 'Location'), ('REGION', 'Region')]
    STATUS_CHOICES = [('PENDING', 'Pending'), ('RUNNING', 'Running'), ('SUCCESS', 'Success'), ('FAILED', 'Failed'), ('STOPPED', 'Stopped')]

    scheduler = models.ForeignKey(Scheduler, on_delete=models.SET_NULL, null=True, blank=True)
    execution_type = models.CharField(max_length=50, choices=EXECUTION_TYPES, null=True, blank=True)
    scope_type = models.CharField(max_length=50, choices=SCOPE_TYPES, null=True, blank=True)
    configuration = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True, blank=True)
    total_tasks = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    failed_tasks = models.IntegerField(default=0)
    celery_group_id = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.ForeignKey('core_users.User', on_delete=models.SET_NULL, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class ActiveExecution(BaseExecution):
    class Meta:
        db_table = 'active_executions'


class ExecutionHistory(BaseExecution):
    class Meta:
        db_table = 'execution_history'


class BaseTask(BaseModel):
    """Abstract base class for all tasks (Active and Historical)"""
    status = models.CharField(max_length=50, null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    
class DataDumpTask(BaseTask):
    execution = models.ForeignKey(ActiveExecution, on_delete=models.CASCADE)
    api_dump_id = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True, help_text="Stores keyword, location, or region_json IDs")

    class Meta:
        db_table = 'data_dump_tasks'
        indexes = [
            models.Index(fields=['execution', 'status'], name='idx_datadump_exec_status'),
        ]


class JsonFileTask(BaseTask):
    execution = models.ForeignKey(ActiveExecution, on_delete=models.CASCADE)
    region_json_id = models.CharField(max_length=255, null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True, help_text="Stores keyword, location, or region_json IDs")

    class Meta:
        db_table = 'json_file_tasks'
        indexes = [
            models.Index(fields=['execution', 'status'], name='idx_jsonfile_exec_status'),
        ]

class TaskHistory(BaseTask):
    TASK_TYPES = [
        ('DATA_DUMP', 'Data Dump'), 
        ('JSON_BUILD', 'Json Build')
    ]
    
    # Links to the historical execution
    execution = models.ForeignKey(ExecutionHistory, on_delete=models.CASCADE, related_name='historical_tasks')
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)
    
    # Store a primary ID here (e.g., the region_json ID, or a concatenated string like 'kw:1-loc:2')
    resource_id = models.CharField(max_length=255, null=True, blank=True)
    
    # BEST PRACTICE: Store the exact IDs so you don't lose the link to Keyword/Location
    # e.g., {"keyword_id": 5, "location_id": 12}
    resource_metadata = models.JSONField(null=True, blank=True, help_text="Stores keyword, location, or region_json IDs")

    class Meta:
        db_table = 'task_history'
        indexes = [
            models.Index(fields=['execution', 'task_type'], name='idx_taskhist_exec_type'),
            models.Index(fields=['celery_task_id'], name='idx_taskhist_celery_id'),
        ]