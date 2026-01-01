from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import TimeStampedModel, AuditableMixin, SoftDeleteModel
import random
import string

User = get_user_model()

class LoginHistory(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_history")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    logged_out_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "login_history"


class PasswordResetOTP(TimeStampedModel):
    """OTP for password reset via email"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_otps")
    otp = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = "password_reset_otp"
        ordering = ("-created_at",)
    
    @classmethod
    def generate_otp(cls):
        """Generate a 6-digit OTP"""
        return ''.join(random.choices(string.digits, k=6))
    
    @classmethod
    def create_otp(cls, user):
        """Create a new OTP for user with 10 minute expiry"""
        otp = cls.generate_otp()
        expires_at = timezone.now() + timezone.timedelta(minutes=10)
        return cls.objects.create(user=user, otp=otp, expires_at=expires_at)
    
    def is_valid(self):
        """Check if OTP is still valid"""
        return not self.is_used and timezone.now() <= self.expires_at
    
    def __str__(self):
        return f"OTP for {self.user.email} - {'Valid' if self.is_valid() else 'Invalid'}"