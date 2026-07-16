from rest_framework import serializers
from .models import User, Role
from core.organizations.models import Organization
from shared.base.serializers import BaseModelSerializer

class RoleSerializer(BaseModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name", "code", "role_type")

class OrganizationMinimalSerializer(BaseModelSerializer):
    class Meta:
        model = Organization
        fields = ("id", "name")

class UserSerializer(BaseModelSerializer):
    organization_details = OrganizationMinimalSerializer(source="organization", read_only=True)
    managed_organizations = OrganizationMinimalSerializer(many=True, read_only=True)
    role_details = RoleSerializer(source="role", read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "created_at", "updated_at",
            "name",
            "email",
            "role",
            "role_details",
            "organization",
            "organization_details",
            "managed_organizations",
            "is_active",
        )

class UserCreateUpdateSerializer(BaseModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=False,
        allow_null=True
    )
    managed_organization_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Organization.objects.all(),
        write_only=True,
        required=False,
        source="managed_organizations"
    )

    class Meta:
        model = User
        fields = ("id", "created_at", "updated_at", "name", "email", "role", "organization", "managed_organization_ids", "password")
        extra_kwargs = {
            "password": {"write_only": True, "required": False}
        }

    def create(self, validated_data):
        managed_orgs = validated_data.pop("managed_organizations", [])
        password = validated_data.pop("password", None)

        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()

        if managed_orgs:
            user.managed_organizations.set(managed_orgs)

        return user

    def update(self, instance, validated_data):
        managed_orgs = validated_data.pop("managed_organizations", None)
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if managed_orgs is not None:
            instance.managed_organizations.set(managed_orgs)

        return instance


class PasswordUpdateSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class ProfileSerializer(BaseModelSerializer):
    """Serializer for user profile - shows more details"""
    organization_details = OrganizationMinimalSerializer(source="organization", read_only=True)
    
    class Meta:
        model = User
        fields = (
            "id", "created_at", "updated_at",
            "name",
            "email",
            "role",
            "organization_details",
            "is_active",
        )
        read_only_fields = ("id", "created_at", "updated_at", "email", "role", "is_active")


class ProfileUpdateSerializer(BaseModelSerializer):
    """Serializer for updating user profile"""
    
    class Meta:
        model = User
        fields = ("id", "created_at", "updated_at", "name")


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

