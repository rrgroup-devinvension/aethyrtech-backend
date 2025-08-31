from django.db import models

# Create your models here.
from django.db import models


class ScrapingLog(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"

    platform = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=Status.choices)

    products_found = models.IntegerField(default=0)
    products_updated = models.IntegerField(default=0)
    products_added = models.IntegerField(default=0)
    products_deactivated = models.IntegerField(default=0)

    errors_count = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    error_details = models.JSONField(null=True, blank=True)  # maps to longtext with json_valid check

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)

    summary = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        db_table = "scraping_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.platform}] {self.status} (Found: {self.products_found}, Errors: {self.errors_count})"
