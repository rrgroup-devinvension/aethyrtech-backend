import logging
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import LoginHistory, PasswordResetOTP

logger = logging.getLogger(__name__)
User = get_user_model()

class AuthenticationService:
    @staticmethod
    def record_login(user, ip_address=None, user_agent=None):
        """Records a successful login in LoginHistory."""
        try:
            LoginHistory.objects.create(
                user=user, 
                ip_address=ip_address, 
                user_agent=user_agent
            )
            logger.info(f"Recorded login history for user {user.email}")
        except Exception as e:
            logger.error(f"Failed to record login history for user {user.email}: {str(e)}")

    @staticmethod
    def record_logout(user):
        """Marks the active login session as logged out."""
        try:
            updated = LoginHistory.objects.filter(
                user=user, 
                logged_out_at__isnull=True
            ).update(logged_out_at=timezone.now())
            logger.info(f"Recorded logout for user {user.email}, updated {updated} sessions.")
        except Exception as e:
            logger.error(f"Failed to record logout for user {user.email}: {str(e)}")

    @staticmethod
    def generate_and_send_otp(user):
        """Generates an OTP for password reset and sends it via email."""
        # Create OTP
        otp_instance = PasswordResetOTP.create_otp(user)
        logger.info(f"Generated password reset OTP for user {user.email}")
        
        # Send email with OTP
        try:
            send_mail(
                subject='Password Reset OTP - AethyrTech',
                message=f'Your OTP for password reset is: {otp_instance.otp}\n\nThis OTP will expire in 10 minutes.\n\nIf you did not request this, please ignore this email.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"Sent password reset OTP email to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP email to {user.email}: {str(e)}")
            return False

    @staticmethod
    def verify_otp(user, otp):
        """Verifies if the provided OTP is valid for the given user."""
        try:
            otp_instance = PasswordResetOTP.objects.filter(
                user=user,
                otp=otp,
                is_used=False
            ).latest('created_at')
        except PasswordResetOTP.DoesNotExist:
            logger.warning(f"Failed OTP verification for user {user.email}: OTP not found or already used.")
            return False, "Invalid OTP"
        
        if not otp_instance.is_valid():
            logger.warning(f"Failed OTP verification for user {user.email}: OTP expired.")
            return False, "OTP has expired or already been used"
            
        logger.info(f"Successfully verified OTP for user {user.email}")
        return True, otp_instance

    @staticmethod
    def reset_password(user, otp_instance, new_password):
        """Resets the user's password and marks the OTP as used."""
        try:
            user.set_password(new_password)
            user.save()
            
            otp_instance.is_used = True
            otp_instance.save()
            
            logger.info(f"Successfully reset password for user {user.email}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset password for user {user.email}: {str(e)}")
            return False
