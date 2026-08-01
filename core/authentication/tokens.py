from django.contrib.auth.tokens import PasswordResetTokenGenerator as DjangoPasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from core.users.models import User


class PasswordResetTokenGenerator(DjangoPasswordResetTokenGenerator):
    """Custom password reset token generator extending Django's default.

    Provides utility methods to simultaneously generate and encode a user ID (uid)
    along with the secure reset token, and to decode and validate them.
    """
    def make_token(self, user):
        """Generate a URL-safe encoded user ID (uid) and a secure reset token.

        Returns:
            tuple: A pair containing the base64 encoded user ID and the reset token.
        """
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = super().make_token(user)
        return uid, token

    def validate_token(self, uid: str, token: str):
        """Decode the provided uid and validate the token for the associated user.

        Returns:
            User: The authenticated user instance if valid, or None if invalid or expired.
        """
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None
        if super().check_token(user, token):
            return user
        return None
