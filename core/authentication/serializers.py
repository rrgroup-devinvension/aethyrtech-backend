from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from core.users.models import User


class LoginSerializer(serializers.Serializer):
    """Serializer for handling user login requests.

    Validates user credentials and returns a JWT access and refresh token pair
    along with basic user profile and permission data.
    """
    email = serializers.EmailField()
    password = serializers.CharField(max_length=191, write_only=True)

    def validate(self, data):
        """Validate the provided email and password.

        Authenticates the user and generates new JWT tokens if successful.
        Also compiles the user's role and effective permissions to be included
        in the response payload.
        """
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not isinstance(user, User):
            raise serializers.ValidationError("Invalid user type")
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        role_code = user.role.code if user.role else None
        effective_permissions = user.get_all_permissions()

        effective_user_type = user.user_type or (user.role.role_type if user.role else None)

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": getattr(user, "name", ""),
                "role": role_code,
                "user_type": effective_user_type,
                "permissions": effective_permissions
            },
            "refresh": str(refresh),
            "refresh_expires": refresh.payload.get('exp'),
            "access": str(access_token),
            "access_expires": access_token.payload.get('exp'),
        }

class RefreshSerializer(serializers.Serializer):
    """Serializer for refreshing expired JWT access tokens.

    Accepts a valid refresh token and issues a new access token, along with
    the updated user profile and permission data.
    """
    refresh = serializers.CharField()

    def validate(self, data):
        """Validate the provided refresh token.

        Decodes the token to find the associated user, ensures the user still
        exists, and generates a new access token.
        """
        try:
            refresh = RefreshToken(data["refresh"])
        except TokenError as err:
            raise serializers.ValidationError("Invalid or expired refresh token") from err

        access_token = refresh.access_token

        # Get user from token
        user_id = refresh.payload.get("user_id")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist as err:
            raise serializers.ValidationError("User not found") from err

        role_code = user.role.code if user.role else None
        effective_permissions = user.get_all_permissions()

        effective_user_type = user.user_type or (user.role.role_type if user.role else None)

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": getattr(user, "name", ""),
                "role": role_code,
                "user_type": effective_user_type,
                "permissions": effective_permissions,
            },
            "refresh": str(refresh),
            "refresh_expires": refresh.payload.get("exp"),
            "access": str(access_token),
            "access_expires": access_token.payload.get("exp"),
        }

class LogoutSerializer(serializers.Serializer):
    """Serializer for handling user logout requests.

    Accepts a refresh token so that it can be blacklisted or invalidated
    on the backend.
    """
    refresh = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for initiating the forgot password flow.

    Accepts an email address and triggers the generation of an OTP (One Time Password).
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        """Verify that the provided email belongs to an active, non-deleted account."""
        try:
            User.objects.get(email=value, is_active=True, is_deleted=False)
        except User.DoesNotExist as err:
            raise serializers.ValidationError("No active account found with this email address") from err
        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying the OTP sent to the user's email.

    Ensures the 6-digit OTP matches what was generated during the forgot password flow.
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for setting a new password.

    Accepts the email, the verified OTP, and the new password pair.
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        """Ensure that the new password and confirm password fields match exactly."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data
