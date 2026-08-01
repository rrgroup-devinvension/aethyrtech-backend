from django.core.validators import URLValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from shared.base.models import BaseModel


class Status(models.TextChoices):
    """Status choices."""
    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    DEPRECATED = "DEPRECATED", _("Deprecated")

class AuthType(models.TextChoices):
    """Auth type choices."""
    NONE = "NONE", _("None")
    API_KEY = "API_KEY", _("API Key")
    BASIC = "BASIC", _("Basic Auth")
    BEARER = "BEARER", _("Bearer Token")
    OAUTH2 = "OAUTH2", _("OAuth2")
    JWT = "JWT", _("JWT")
    CUSTOM = "CUSTOM", _("Custom")

class HttpMethod(models.TextChoices):
    """HTTP method choices."""
    GET = "GET", _("GET")
    POST = "POST", _("POST")
    PUT = "PUT", _("PUT")
    PATCH = "PATCH", _("PATCH")
    DELETE = "DELETE", _("DELETE")

class ApiProvider(BaseModel):
    """Model representing an external API integration, storing connection details, credentials, and health status."""
    name = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text="Unique provider name"
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique internal identifier (e.g. STRIPE, TWILIO)"
    )
    base_url = models.URLField(
        max_length=500,
        validators=[URLValidator()]
    )
    api_version = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )
    auth_type = models.CharField(
        max_length=20,
        choices=AuthType.choices,
        default=AuthType.NONE
    )
    default_headers = models.JSONField(
        default=dict,
        blank=True
    )
    credentials = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Keys/tokens. MUST BE ENCRYPTED at the application/database layer.")
    )
    timeout = models.PositiveIntegerField(
        default=30,
        help_text="Timeout in seconds"
    )
    retry_count = models.PositiveSmallIntegerField(
        default=3
    )
    retry_delay = models.PositiveSmallIntegerField(
        default=2,
        help_text="Retry delay in seconds"
    )
    health_check_path = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Path to check API health (e.g., '/health')")
    )
    test_http_method = models.CharField(
        max_length=10,
        choices=HttpMethod.choices,
        default=HttpMethod.GET,
        help_text=_("HTTP method used for health checks and connection testing")
    )
    test_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Payload sent during health checks (for POST/PUT/PATCH)")
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    health_check_status = models.CharField(
        max_length=50,
        blank=True,
        default=''
    )
    last_health_check = models.DateTimeField(
        null=True,
        blank=True
    )
    description = models.TextField(
        blank=True,
        default=''
    )

    class Meta:
        db_table = 'api_providers'

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        # Store original values to check if they changed
        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_credentials = self.credentials
        self._original_auth_type = self.auth_type

    def get_decrypted_credentials(self) -> dict:
        """Helper to securely decrypt the stored credentials."""
        from .utils import decrypt_dict

        if not self.credentials:
            return {}

        encrypted_payload = self.credentials.get("encrypted_payload")
        if encrypted_payload:
            return decrypt_dict(encrypted_payload)

        # Legacy support: if credentials are still in plain-text JSON
        return self.credentials

    def save(self, *args, **kwargs):
        """Save model."""
        from .utils import encrypt_dict

        # Encrypt plain-text credentials if they are assigned
        if self.credentials and "encrypted_payload" not in self.credentials:
            self.credentials = {
                "encrypted_payload": encrypt_dict(self.credentials)
            }

        # Reset health check if critical connection fields changed
        if self.pk and (
            self.base_url != self._original_base_url or
            self.health_check_path != self._original_health_check_path or
            self.credentials != self._original_credentials or
            self.auth_type != self._original_auth_type
        ):
            self.health_check_status = ''

        super().save(*args, **kwargs)

        # Update original values after save
        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_credentials = self.credentials
        self._original_auth_type = self.auth_type


class APIUsageLog(BaseModel):
    """Model for tracking raw, individual API requests, including latency, status, and payload metadata."""
    # Time and Status
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)  # e.g., 'SUCCESS', 'FAILED', 'TIMEOUT'
    error_message = models.TextField(blank=True, default='')

    # Internal Foreign Keys (References to other Experience Cloud models)
    api_provider = models.ForeignKey('ApiProvider', on_delete=models.SET_NULL, null=True, blank=True)
    platform = models.ForeignKey('experience_cloud_catalog.Platform', on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey('core_categories.Category', on_delete=models.SET_NULL, null=True, blank=True)
    keyword_name = models.CharField(max_length=255, blank=True, default='')
    location_name = models.CharField(max_length=255, blank=True, default='')

    # Cross-Boundary Soft References (References to Core Foundation)
    brand_ids = models.TextField(blank=True, default='', help_text="Comma-separated brand IDs")
    brand_names = models.TextField(blank=True, default='', help_text="Comma-separated brand names")
    region_ids = models.TextField(blank=True, default='', help_text="Comma-separated region IDs")
    region_names = models.TextField(blank=True, default='', help_text="Comma-separated region names")

    # Metrics
    response_time = models.FloatField(null=True, blank=True) # In milliseconds or seconds
    cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.00)
    request_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes")
    response_size = models.IntegerField(null=True, blank=True, help_text="Size in bytes")

    class Meta:
        db_table = 'api_usage_logs'
        indexes = (
            models.Index(fields=['timestamp']),
            models.Index(fields=['api_provider', 'status']),
        )


class APIUsageSummary(BaseModel):
    """Model for storing aggregated, daily metrics of API usage to drive dashboards and analytics."""
    date = models.DateField()

    # Internal Foreign Keys
    api_provider = models.ForeignKey('ApiProvider', on_delete=models.CASCADE)
    platform = models.ForeignKey('experience_cloud_catalog.Platform', on_delete=models.CASCADE, null=True, blank=True)

    # Cross-Boundary Soft References
    brand_id = models.IntegerField(null=True, blank=True)
    brand_name = models.CharField(max_length=255, blank=True, default='')
    region_id = models.IntegerField(null=True, blank=True)
    region_name = models.CharField(max_length=255, blank=True, default='')

    # Aggregated Metrics
    total_calls = models.IntegerField(default=0)
    success_calls = models.IntegerField(default=0)
    failed_calls = models.IntegerField(default=0)
    average_response_time = models.FloatField(default=0.0)
    total_products = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=6, default=0.00)

    class Meta:
        db_table = 'api_usage_summaries'
        # Unique constraint ensures we only have one summary row per dimension combination per day
        constraints = (
            models.UniqueConstraint(
                fields=['date', 'api_provider', 'platform', 'brand_id', 'region_id'],
                name='unique_api_summary_dimension'
            ),
        )
        indexes = (
            models.Index(fields=['date']),
            models.Index(fields=['brand_id', 'date']),
        )
