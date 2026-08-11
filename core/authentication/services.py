import logging
import smtplib

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import DatabaseError
from django.utils import timezone

from .models import LoginHistory, PasswordResetOTP

logger = logging.getLogger(__name__)
User = get_user_model()

class AuthenticationService:
    """Service class handling business logic for authentication.

    Provides methods for tracking user logins/logouts, generating OTPs,
    and managing the password reset flow.
    """
    @staticmethod
    def record_login(user, ip_address=None, user_agent=None):
        """Record a successful login event for auditing and security monitoring.

        Saves the user's IP address and browser agent in the LoginHistory model.
        """
        try:
            LoginHistory.objects.create(
                user=user,
                ip_address=ip_address,
                user_agent=user_agent
            )
            logger.info(f"Recorded login history for user {user.email}")
        except DatabaseError as e:
            logger.error(f"Failed to record login history for user {user.email}: {e!s}")

    @staticmethod
    def record_logout(user):
        """Mark all active login sessions for the user as logged out.

        Finds any LoginHistory entries without a logout timestamp and updates
        them with the current time.
        """
        try:
            updated = LoginHistory.objects.filter(
                user=user,
                logged_out_at__isnull=True
            ).update(logged_out_at=timezone.now())
            logger.info(f"Recorded logout for user {user.email}, updated {updated} sessions.")
        except DatabaseError as e:
            logger.error(f"Failed to record logout for user {user.email}: {e!s}")

    @staticmethod
    def generate_and_send_otp(user):
        """Generate a secure One-Time Password and dispatch it to the user's email.

        Creates a PasswordResetOTP database record and triggers the Django
        send_mail utility to deliver it. Returns True if the email was sent successfully.
        """
        # Create OTP
        otp_instance = PasswordResetOTP.create_otp(user)
        logger.info(f"Generated password reset OTP for user {user.email}")

        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        context = {
            'user_email': user.email,
            'otp': otp_instance.otp
        }

        html_message = render_to_string('emails/password_reset.html', context)
        plain_message = strip_tags(html_message)

        # Send email with OTP
        try:
            send_mail(
                subject='Password Reset OTP - AethyrTech',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Sent password reset OTP email to {user.email}")
            return True
        except (smtplib.SMTPException, OSError) as e:
            logger.error(f"Failed to send OTP email to {user.email}: {e!s}")
            return False

    @staticmethod
    def verify_otp(user, otp):
        """Validate the provided OTP against the user's active tokens.

        Checks that the OTP exists, belongs to the correct user, hasn't been used yet,
        and hasn't expired. Returns a boolean indicating success and either the
        OTP instance or an error message.
        """
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
        """Update the user's password and invalidate the used OTP.

        Applies the new hashed password to the user model and marks the
        PasswordResetOTP instance as used so it cannot be reused.
        """
        try:
            user.set_password(new_password)
            user.save()

            otp_instance.is_used = True
            otp_instance.save()

            logger.info(f"Successfully reset password for user {user.email}")
            return True
        except DatabaseError as e:
            logger.error(f"Failed to reset password for user {user.email}: {e!s}")
            return False
