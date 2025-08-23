from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .tokens import PasswordResetTokenGenerator


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ("id", "email", "name", "role", "brands", "created_at", "updated_at")


class UserCreateUpdateSerializer(serializers.ModelSerializer):
    brand_ids = serializers.ListField(write_only=True, required=False, child=serializers.IntegerField())

    class Meta:
        model = User
        fields = ("email", "name", "role", "brand_ids", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        brand_ids = validated_data.pop("brand_ids", [])
        password = validated_data.pop("password", None)
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        if brand_ids:
            user.brands.set(brand_ids)
        return user

    def update(self, instance, validated_data):
        brand_ids = validated_data.pop("brand_ids", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if brand_ids is not None:
            instance.brands.set(brand_ids)
        return instance


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        refresh = RefreshToken.for_user(user)
        return {
            "user": {"id": str(user.id), "email": user.email, "name": user.name, "role": user.role},
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if not user.is_active:
            raise serializers.ValidationError("User account is inactive")
        refresh = RefreshToken.for_user(user)
        return {
            "user": {"id": str(user.id), "email": user.email, "name": user.name},
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("No active user with this email")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    uid = serializers.CharField()
    new_password = serializers.CharField(min_length=6)

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