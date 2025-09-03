from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .tokens import PasswordResetTokenGenerator


User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=191, write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        return {
            "user": {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role},
            "refresh": str(refresh),
            "refresh_expires": refresh.payload.get('exp'),
            "access": str(access_token),
            "access_expires": access_token.payload.get('exp'),
        }

class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, data):
        try:
            refresh = RefreshToken(data["refresh"])
        except TokenError:
            raise serializers.ValidationError("Invalid or expired refresh token")

        access_token = refresh.access_token

        # Get user from token
        user_id = refresh.payload.get("user_id")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": getattr(user, "name", ""),
                "role": getattr(user, "role", ""),
            },
            "refresh": str(refresh),
            "refresh_expires": refresh.payload.get("exp"),
            "access": str(access_token),
            "access_expires": access_token.payload.get("exp"),
        }
    
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()



class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("No active user with this email")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=191)
    uid = serializers.CharField(max_length=191)
    new_password = serializers.CharField(min_length=6, max_length=191)

    def validate(self, data):
        token_gen = PasswordResetTokenGenerator()
        user = token_gen.validate_token(data["uid"], data["token"])
        if not user:
            raise serializers.ValidationError("Invalid or expired token")
        data["user"] = user
        return data

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user