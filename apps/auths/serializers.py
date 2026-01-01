from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


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
        try:
            user = User.objects.get(email=value, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            raise serializers.ValidationError("No active account found with this email address")
        return value


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data
