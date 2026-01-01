from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel
from django.db.models import JSONField


class Scheduler(TimeStampedModel, AuditableMixin):
    class TriggerType(models.TextChoices):
        CRON = "CRON", "Cron"
        MANUAL = "MANUAL", "Manual"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50, choices=(('KEYWORD_SYNC','KEYWORD_SYNC'),('JSON_BUILD','JSON_BUILD')))
    trigger_type = models.CharField(max_length=20, choices=TriggerType.choices, default=TriggerType.MANUAL)
    cron_expression = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "scheduler"

    def __str__(self):
        return f"{self.name} ({self.type})"


class SchedulerJob(TimeStampedModel, AuditableMixin):
    class TriggeredBy(models.TextChoices):
        SYSTEM = "SYSTEM", "System"
        ADMIN = "ADMIN", "Admin"

    class ScopeType(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        KEYWORD = "KEYWORD", "Keyword"
        BRAND = "BRAND", "Brand"
        JSON = "JSON", "JSON"

    class TaskGroup(models.TextChoices):
        DATA_DUMP = "DATA_DUMP", "Data Dump"
        JSON_BUILD = "JSON_BUILD", "JSON Build"
        BOTH = "BOTH", "Both"

    class JobStatus(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        PARTIAL = "PARTIAL", "Partial"

    scheduler = models.ForeignKey(Scheduler, null=True, blank=True, on_delete=models.SET_NULL, related_name='jobs')
    triggered_by = models.CharField(max_length=20, choices=TriggeredBy.choices, default=TriggeredBy.SYSTEM)
    scope_type = models.CharField(max_length=20, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    scope_id = models.BigIntegerField(null=True, blank=True)
    task_group = models.CharField(max_length=20, choices=TaskGroup.choices, default=TaskGroup.BOTH)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.RUNNING)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "scheduler_job"

    def __str__(self):
        return f"Job {self.id} for {self.scheduler}"


class Task(TimeStampedModel, AuditableMixin):
    class TaskType(models.TextChoices):
        DATA_DUMP = "DATA_DUMP", "Data Dump"
        JSON_BUILD = "JSON_BUILD", "JSON Build"

    class EntityType(models.TextChoices):
        KEYWORD = "KEYWORD", "Keyword"
        BRAND = "BRAND", "Brand"
        JSON_FILE = "JSON_FILE", "JSON File"

    class TaskStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    scheduler_job = models.ForeignKey(SchedulerJob, null=True, blank=True, on_delete=models.CASCADE, related_name='tasks')
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.BigIntegerField(null=True, blank=True)
    entity_name = models.CharField(max_length=255, blank=True)
    extra_context = JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    retry_of_task = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "scheduler_task"

    def __str__(self):
        return f"Task {self.id} [{self.task_type}] for {self.entity_type}:{self.entity_id}"


class Pincode(SoftDeleteModel, AuditableMixin):
    """Pincode master data for data dump operations."""
    pincode = models.CharField(max_length=10, unique=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "pincode"
        ordering = ('pincode',)

    def __str__(self):
        return self.pincode


class Keyword(SoftDeleteModel, AuditableMixin):
    """Keyword master data for data dump operations."""
    keyword = models.CharField(max_length=255)
    pincode = models.ForeignKey(Pincode, on_delete=models.CASCADE, related_name='keywords')
    is_active = models.BooleanField(default=True)
    
    # Task tracking
    last_running_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='running_keywords')
    last_completed_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='completed_keywords')
    last_synced = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "keyword"
        unique_together = [['keyword', 'pincode']]
        ordering = ('keyword', 'pincode')

    def __str__(self):
        return f"{self.keyword} - {self.pincode.pincode}"


class BrandJsonFile(SoftDeleteModel, AuditableMixin):
    """Stores latest JSON file metadata for a brand and template.

    - `brand` and `template` are unique together.
    - `file_path` holds the relative MEDIA path to the file (do not modify on error).
    - `error_message` stores last error if generation failed.
    - `last_synced` denotes last attempt time (success or failure).
    """
    brand = models.ForeignKey('brand.Brand', on_delete=models.CASCADE, related_name='json_files')
    template = models.CharField(max_length=255)
    filename = models.CharField(max_length=1024, null=True, blank=True)
    file_path = models.CharField(max_length=2048, null=True, blank=True)
    
    # Task tracking
    last_running_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='running_json_files')
    last_completed_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='completed_json_files')
    last_synced = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'brand_json_file'
        unique_together = (('brand', 'template'),)

    def __str__(self):
        return f"BrandJsonFile {self.brand_id}:{self.template}"
