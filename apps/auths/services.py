from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .tokens import PasswordResetTokenGenerator

User = get_user_model()

def send_password_reset_email(user: User):
    token_gen = PasswordResetTokenGenerator()
    uid, token = token_gen.make_token(user)

    reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"

    subject = "Password Reset Request"
    message = f"Hi {user.name or 'User'},\n\nUse this link to reset your password:\n{reset_url}\n\nIf you did not request this, please ignore."
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
    return True
