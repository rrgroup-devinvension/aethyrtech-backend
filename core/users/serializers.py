from rest_framework import serializers

from core.organizations.models import Brand, Organization, Region
from shared.base.serializers import BaseModelSerializer

from .models import Role, User


class RoleSerializer(BaseModelSerializer):
    """Serializer for role."""
    permissions_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Role
        fields = ("id", "name", "code", "role_type", "permissions", "is_active", "permissions_count")

    def get_permissions_count(self, obj):
        """Get permissions count."""
        return 0  # Replaced in to_representation

    def to_representation(self, instance):
        """Convert to dict."""
        ret = super().to_representation(instance)
        if instance.code and instance.code.upper() == 'ADMIN':
            from core.authentication.permissions import PERMISSION_REGISTRY
            ret['permissions'] = [p["id"] for p in PERMISSION_REGISTRY if 'INTERNAL' in p.get('scopes', [])]

        ret['permissions_count'] = len(ret.get('permissions') or [])
        return ret

class OrganizationMinimalSerializer(BaseModelSerializer):
    """Minimal serializer for organization."""
    class Meta(BaseModelSerializer.Meta):
        model = Organization
        fields = ("id", "name")




class UserRegionSerializer(BaseModelSerializer):
    """Serializer for region."""
    class Meta(BaseModelSerializer.Meta):
        model = Region
        fields = ("id", "name", "code")

class UserBrandRegionSerializer(BaseModelSerializer):
    """Serializer for brand and regions."""
    regions = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Brand
        fields = ("id", "name", "code", "logo", "regions")

    def get_regions(self, obj):
        """Get regions."""
        active_regions = obj.region_set.filter(is_active=True, is_deleted=False)
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            if user.regions.exists():
                active_regions = active_regions.filter(id__in=user.regions.all())
        return UserRegionSerializer(active_regions, many=True).data


class UserSerializer(BaseModelSerializer):
    """Serializer for user."""
    organization_details = OrganizationMinimalSerializer(source="organization", read_only=True)
    managed_organizations = OrganizationMinimalSerializer(many=True, read_only=True)
    role_details = RoleSerializer(source="role", read_only=True)
    brands_details = UserBrandRegionSerializer(source="brands", many=True, read_only=True)
    regions_details = UserRegionSerializer(source="regions", many=True, read_only=True)

    permissions_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
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
            "extra_permissions",
            "user_type",
            "is_active",
            "phone_number",
            "brands",
            "brands_details",
            "regions",
            "regions_details",
            "permissions_count",
        )

    def get_permissions_count(self, obj):
        return len(obj.get_all_permissions())

class UserCreateUpdateSerializer(BaseModelSerializer):
    """Serializer for creating and updating user."""
    organization: serializers.Field = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=False,
        allow_null=True
    )
    managed_organization_ids: serializers.Field = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Organization.objects.all(),
        write_only=True,
        required=False,
        source="managed_organizations"
    )
    brand_ids: serializers.Field = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Brand.objects.all(),
        write_only=True,
        required=False,
        source="brands"
    )
    region_ids: serializers.Field = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Region.objects.all(),
        write_only=True,
        required=False,
        source="regions"
    )

    class Meta(BaseModelSerializer.Meta):
        model = User
        fields = ("id", "created_at", "updated_at", "name", "email", "phone_number", "role", "organization", "managed_organization_ids", "brand_ids", "region_ids", "password", "extra_permissions", "user_type", "is_active")  # noqa: E501
        extra_kwargs = {  # noqa: RUF012
            "password": {"write_only": True, "required": False}
        }

    def create(self, validated_data):
        """Create instance."""
        managed_orgs = validated_data.pop("managed_organizations", [])
        brands = validated_data.pop("brands", [])
        regions = validated_data.pop("regions", [])
        password = validated_data.pop("password", None)

        role = validated_data.get("role")
        user_type = validated_data.get("user_type")
        if not user_type and role:
            validated_data["user_type"] = role.role_type

        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()

        if managed_orgs:
            user.managed_organizations.set(managed_orgs)
        if brands:
            user.brands.set(brands)
        if regions:
            user.regions.set(regions)

        return user

    def update(self, instance, validated_data):
        """Update instance."""
        managed_orgs = validated_data.pop("managed_organizations", None)
        brands = validated_data.pop("brands", None)
        regions = validated_data.pop("regions", None)
        password = validated_data.pop("password", None)

        role = validated_data.get("role", instance.role)
        user_type = validated_data.get("user_type", instance.user_type)
        if not user_type and role:
            validated_data["user_type"] = role.role_type

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if managed_orgs is not None:
            instance.managed_organizations.set(managed_orgs)
        if brands is not None:
            instance.brands.set(brands)
        if regions is not None:
            instance.regions.set(regions)

        return instance


class PasswordUpdateSerializer(serializers.Serializer):
    """Serializer for password update."""
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        """Validate data."""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class ProfileSerializer(BaseModelSerializer):
    """Serializer for user profile - shows more details."""
    organization_details = OrganizationMinimalSerializer(source="organization", read_only=True)
    role_details = RoleSerializer(source="role", read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = User
        fields = (
            "id", "created_at", "updated_at",
            "name",
            "email",
            "role",
            "role_details",
            "organization_details",
            "is_active",
        )
        read_only_fields = ("id", "created_at", "updated_at", "email", "role", "is_active")


class ProfileUpdateSerializer(BaseModelSerializer):
    """Serializer for updating user profile."""

    class Meta(BaseModelSerializer.Meta):
        model = User
        fields = ("id", "created_at", "updated_at", "name")


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (requires current password)."""
    current_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True, required=True)

    def validate_current_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value

    def validate(self, data):
        """Validate new password match."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError({"new_password": "New password must be different from current password"})
        return data


class ContactUsSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    mobile = serializers.CharField(max_length=20, required=False, allow_blank=True)
    message = serializers.CharField()
