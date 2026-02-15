from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel
from django.db.models import JSONField


class Scheduler(TimeStampedModel, AuditableMixin):
    """Scheduler configuration for cron jobs."""
    
    class SchedulerType(models.TextChoices):
        DATA_DUMP = 'DATA_DUMP', 'Data Dump'
        JSON_BUILD = 'JSON_BUILD', 'JSON Build'
    
    class TriggerType(models.TextChoices):
        MANUAL = 'MANUAL', 'Manual'
        CRON = 'CRON', 'Cron'
    
    class SchedulerStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        INACTIVE = 'INACTIVE', 'Inactive'
    
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=50, choices=SchedulerType.choices)
    trigger_type = models.CharField(max_length=50, choices=TriggerType.choices, default=TriggerType.MANUAL)
    cron_expression = models.CharField(max_length=255, blank=True, null=True, help_text='Cron expression for scheduled jobs')
    status = models.CharField(max_length=20, choices=SchedulerStatus.choices, default=SchedulerStatus.ACTIVE)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'scheduler'
    
    def __str__(self):
        return f"{self.name} ({self.type})"


class SchedulerJob(TimeStampedModel, AuditableMixin):
    class TriggeredBy(models.TextChoices):
        SYSTEM = "SYSTEM", "System"
        ADMIN = "ADMIN", "Admin"

    class ScopeType(models.TextChoices):
        GLOBAL = "GLOBAL", "Global"
        KEYWORD = "KEYWORD", "Keyword"
        PINCODE = "PINCODE", "Pincode"
        BRAND = "BRAND", "Brand"
        JSON = "JSON", "JSON"

    class TaskGroup(models.TextChoices):
        DATA_DUMP = "DATA_DUMP", "Data Dump"
        JSON_BUILD = "JSON_BUILD", "JSON Build"

    class JobStatus(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        PARTIAL = "PARTIAL", "Partial"
        STOPPED = "STOPPED", "Stopped"

    scheduler = models.ForeignKey(
        Scheduler,
        on_delete=models.CASCADE,
        related_name='jobs',
        null=True,
        blank=True,
        help_text='Scheduler that triggered this job (null for manual runs)'
    )
    triggered_by = models.CharField(max_length=20, choices=TriggeredBy.choices, default=TriggeredBy.SYSTEM)
    scope_type = models.CharField(max_length=20, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    scope_id = models.CharField(max_length=255, null=True, blank=True)
    task_group = models.CharField(max_length=20, choices=TaskGroup.choices)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.RUNNING)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "scheduler_job"

    def __str__(self):
        scheduler_name = self.scheduler.name if self.scheduler else 'Manual'
        return f"Job {self.id} - {scheduler_name} - {self.task_group} ({self.status})"


class Task(TimeStampedModel, AuditableMixin):
    class TaskType(models.TextChoices):
        DATA_DUMP = "DATA_DUMP", "Data Dump"
        JSON_BUILD = "JSON_BUILD", "JSON Build"

    class EntityType(models.TextChoices):
        KEYWORD_PINCODE = "KEYWORD_PINCODE", "Keyword Pincode"
        BRAND = "BRAND", "Brand"
        JSON_FILE = "JSON_FILE", "JSON File"

    class TaskStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        STOPPED = "STOPPED", "Stopped"

    scheduler_job = models.ForeignKey(SchedulerJob, null=True, blank=True, on_delete=models.CASCADE, related_name='tasks')
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.BigIntegerField(null=True, blank=True)
    entity_name = models.CharField(max_length=255, blank=True)
    extra_context = JSONField(null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    retry_of_task = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = "scheduler_task"

    def __str__(self):
        return f"Task {self.id} [{self.task_type}] for {self.entity_type}:{self.entity_id}"

class KeywordPincode(SoftDeleteModel, AuditableMixin):
    keyword = models.CharField(max_length=255)
    pincode = models.CharField(max_length=32)
    at_synced_with_xbyte = models.DateTimeField(null=True, blank=True)
    synced_with_xbyte = models.BooleanField(null=True, blank=True)
    
    # Task tracking
    last_running_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='running_keywords')
    last_completed_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='completed_keywords')
    last_synced = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "keyword_pincode"
        unique_together = [['keyword', 'pincode']]
        ordering = ('keyword', 'pincode')
        indexes = [
            models.Index(fields=["keyword", "pincode"]),
        ]

    def __str__(self):
        return f"{self.keyword} - {self.pincode}"


class BrandJsonTask(SoftDeleteModel, AuditableMixin):
    brand = models.ForeignKey('brand.Brand',on_delete=models.CASCADE,related_name='brand_json_task')
    last_running_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='running_brand_files')
    last_completed_task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.SET_NULL, related_name='completed_brand_files')
    last_synced = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'brand_json_task'
        constraints = [
            models.UniqueConstraint(fields=['brand'], name='unique_brand_json_task')
        ]

    def __str__(self):
        return f"BrandTaskFile {self.brand_id}"

class BrandJsonFile(SoftDeleteModel, AuditableMixin):
    brand = models.ForeignKey('brand.Brand', on_delete=models.CASCADE, related_name='json_files')
    template = models.CharField(max_length=255)
    filename = models.CharField(max_length=1024, null=True, blank=True)
    file_path = models.CharField(max_length=2048, null=True, blank=True)    
    last_run_time = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=50, null=True)
    last_completed_time = models.DateTimeField(null=True, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'brand_json_file'
        unique_together = (('brand', 'template'),)

    def __str__(self):
        return f"BrandJsonFile {self.brand_id}:{self.template}"

class QuickCommerceSearch(models.Model):
    task_id = models.BigIntegerField()
    keyword = models.CharField(max_length=255)
    pincode = models.CharField(max_length=10)
    platform = models.CharField(max_length=50)
    request_time = models.DateTimeField(null=True)
    response_time = models.DateTimeField(null=True)
    process_time = models.FloatField()
    status_code = models.IntegerField()
    status = models.CharField(max_length=50)
    response_file = models.CharField(max_length=500)
    response_file_size = models.BigIntegerField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "qc_search"

class QuickCommerceProduct(models.Model):
    search = models.ForeignKey(
        QuickCommerceSearch,
        related_name="products",
        on_delete=models.CASCADE
    )
    rank = models.IntegerField()
    product_uid = models.CharField(max_length=100)
    title = models.CharField(max_length=500)
    brand = models.CharField(max_length=255, null=True)
    platform = models.CharField(max_length=255, null=True)
    keyword = models.CharField(max_length=255, null=True)
    pincode = models.CharField(max_length=255, null=True)
    category = models.CharField(max_length=255, null=True)
    availability = models.CharField(max_length=100)
    detail_page_images = models.TextField(null=True)
    msrp = models.CharField(max_length=50, null=True, blank=True)
    sell_price = models.CharField(max_length=50, null=True, blank=True)
    rating = models.CharField(max_length=20, null=True, blank=True)
    reviews = models.CharField(max_length=50, null=True, blank=True)
    product_url = models.TextField(max_length=1000)
    thumbnail = models.TextField(max_length=1000)
    main_image = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "qc_products"
        indexes = [
            models.Index(fields=['product_uid']),
            models.Index(fields=['title']),
        ]

class QuickCommerceProductDetail(models.Model):
    product = models.OneToOneField(
        QuickCommerceProduct,
        on_delete=models.CASCADE,
        related_name="detail"
    )
    model = models.CharField(max_length=255, null=True, blank=True)
    manufacturer_part = models.CharField(max_length=255, null=True, blank=True)
    upc_retailer_id = models.CharField(max_length=100, null=True, blank=True)
    sold_by = models.CharField(max_length=255, null=True, blank=True)
    shipped_by = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    bullets = models.JSONField(default=list, blank=True)
    image_count = models.IntegerField(default=0)
    video_count = models.IntegerField(default=0)
    document_count = models.IntegerField(default=0)
    product_view_360 = models.BooleanField(default=False)
    run_date = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "qc_product_detail"

    def save(self, *args, **kwargs):
        if not self.bullets:
            self.bullets = []
        elif isinstance(self.bullets, str):
            self.bullets = [self.bullets.strip()]
        elif isinstance(self.bullets, list):
            self.bullets = [b.strip() for b in self.bullets if b and b.strip()]
        super().save(*args, **kwargs)

