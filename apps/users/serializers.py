from rest_framework import serializers
from .models import User
from apps.brand.models import Brand
from apps.brand.serializers import BrandSerializer

class UserSerializer(serializers.ModelSerializer):
    brands = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "role",
            "brands",
            "is_active",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
        read_only_fields = ("created_by", "updated_by")
    
    def get_brands(self, obj):
        # Only return active brands
        active_brands = obj.brands.filter(is_active=True)
        return BrandSerializer(active_brands, many=True).data

class UserCreateUpdateSerializer(serializers.ModelSerializer):
    # accept "brands" as a list of IDs
    brands = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Brand.objects.all(),
        write_only=True,
        required=False
    )

    class Meta:
        model = User
        fields = ("name", "email", "role", "brands", "password")
        extra_kwargs = {
            "password": {"write_only": True, "required": False}
        }

    def create(self, validated_data):
        brands = validated_data.pop("brands", [])
        password = validated_data.pop("password", None)

        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()

        if brands:
            user.brands.set(brands)

        return user

    def update(self, instance, validated_data):
        brands = validated_data.pop("brands", None)
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if brands is not None:
            instance.brands.set(brands)

        return instance

class PasswordUpdateSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile - shows more details"""
    brands = BrandSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "role",
            "brands",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "email", "role", "is_active", "created_at", "updated_at")


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ("name",)


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (requires current password)"""
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True, required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError({"new_password": "New password must be different from current password"})
        return data
        password = validated_data.pop("password", None)

        user = User.objects.create(**validated_data)

        if password:
            user.set_password(password)
            user.save()

        if brands:
            user.brands.set(brands)

        return user

    def update(self, instance, validated_data):
        brands = validated_data.pop("brands", None)
        validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if brands is not None:
            instance.brands.set(brands)

        return instance

class PasswordUpdateSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8, max_length=191)
