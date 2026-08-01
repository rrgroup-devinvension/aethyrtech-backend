from rest_framework import serializers

from shared.base.serializers import BaseModelSerializer

from .models import Brand, Competitor, Organization, Region


class OrganizationSerializer(BaseModelSerializer):
    """Serializer for the Organization model.

    Includes dynamically computed fields like the count of active brands
    belonging to the organization.
    """
    brands_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Organization
        fields = (*BaseModelSerializer.Meta.fields, 'name', 'description', 'status', 'brands_count')
        read_only_fields = (*BaseModelSerializer.Meta.read_only_fields, 'brands_count')

    def get_brands_count(self, obj):
        """Calculate the total number of active (non-deleted) brands under this organization."""
        return obj.brand_set.filter(is_deleted=False).count()

    def validate_name(self, value):
        """Ensure the organization name is unique across all active organizations."""
        qs = Organization.objects.filter(is_deleted=False, name__iexact=value)
        if self.instance and isinstance(self.instance, Organization):
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Organization with this name already exists.")
        return value


class CompetitorSerializer(BaseModelSerializer):
    """Serializer for the Competitor model.

    Used to manage competitor data within a specific operational region.
    """
    aliases = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    description = serializers.CharField(allow_null=True, allow_blank=True, required=False)

    class Meta(BaseModelSerializer.Meta):
        model = Competitor
        fields = ('id', 'created_at', 'updated_at', 'region', 'name', 'description', 'aliases', 'is_active')
        read_only_fields = BaseModelSerializer.Meta.read_only_fields

    def validate_aliases(self, value):
        return value or ''

    def validate_description(self, value):
        return value or ''


class BrandSerializer(BaseModelSerializer):
    """Serializer for the Brand model.

    Flattens related foreign key names (organization, category) for easier
    consumption by the frontend client.
    """
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    regions_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Brand
        fields = (
            *BaseModelSerializer.Meta.fields,
            "name", "code", "description", "aliases", "organization",
            "organization_name", "category", "category_name", "is_active",
            "logo", "regions_count"
        )
        read_only_fields = (
            *BaseModelSerializer.Meta.read_only_fields,
            "organization_name", "category_name", "regions_count"
        )

    def get_regions_count(self, obj):
        """Calculate the total number of regions associated with this brand."""
        return obj.region_set.count()

    def validate_name(self, value):
        """Ensure uniqueness of brand name (case-insensitive).

        Allows the current instance to keep its name when editing.
        """
        qs = Brand.objects.filter(is_deleted=False, name__iexact=value)
        if self.instance and isinstance(self.instance, Brand):  # editing
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Brand with this name already exists.")
        return value

class RegionSerializer(BaseModelSerializer):
    """Serializer for the Region model.

    Includes aggregate file counts to give context on region activity.
    """
    brand_name = serializers.CharField(source='brand.name', read_only=True)
    files_count = serializers.SerializerMethodField()

    class Meta(BaseModelSerializer.Meta):
        model = Region
        fields = (*BaseModelSerializer.Meta.fields, 'name', 'code', 'brand', 'brand_name', 'is_active', 'files_count')
        read_only_fields = (*BaseModelSerializer.Meta.read_only_fields, 'brand_name', 'files_count')

    def get_files_count(self, obj):
        """Calculate the number of files generated/associated within this region."""
        from experience_cloud.json_generator.models import JsonTemplate
        return JsonTemplate.objects.count()
