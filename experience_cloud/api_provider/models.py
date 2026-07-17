from django.db import models
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from shared.base.models import BaseModel

class Status(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    INACTIVE = "INACTIVE", _("Inactive")
    DEPRECATED = "DEPRECATED", _("Deprecated")

class AuthType(models.TextChoices):
    NONE = "NONE", _("None")
    API_KEY = "API_KEY", _("API Key")
    BASIC = "BASIC", _("Basic Auth")
    BEARER = "BEARER", _("Bearer Token")
    OAUTH2 = "OAUTH2", _("OAuth2")
    JWT = "JWT", _("JWT")
    CUSTOM = "CUSTOM", _("Custom")

class ApiProvider(BaseModel):
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
        null=True
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
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.ACTIVE
    )
    health_check_status = models.CharField(
        max_length=50, 
        null=True, 
        blank=True
    )
    last_health_check = models.DateTimeField(
        null=True, 
        blank=True
    )
    description = models.TextField(
        null=True, 
        blank=True
    )

    class Meta:
        db_table = 'api_providers'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store original values to check if they changed
        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_credentials = self.credentials
        self._original_auth_type = self.auth_type

    def save(self, *args, **kwargs):
        # Reset health check if critical connection fields changed
        if self.pk:
            if (self.base_url != self._original_base_url or 
                self.health_check_path != self._original_health_check_path or 
                self.credentials != self._original_credentials or
                self.auth_type != self._original_auth_type):
                self.health_check_status = None
        super().save(*args, **kwargs)
        # Update original values after save
        self._original_base_url = self.base_url
        self._original_health_check_path = self.health_check_path
        self._original_credentials = self.credentials
        self._original_auth_type = self.auth_type
