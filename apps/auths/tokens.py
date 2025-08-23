from django.contrib.auth.tokens import PasswordResetTokenGenerator as DjangoPasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import get_user_model

User = get_user_model()

class PasswordResetTokenGenerator(DjangoPasswordResetTokenGenerator):
    def make_token(self, user: User):
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = super().make_token(user)
        return uid, token

    def validate_token(self, uid: str, token: str):
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None
        if super().check_token(user, token):
            return user
        return None
