from rest_framework import serializers
from shared.base.serializers import BaseModelSerializer
from .models import Brand, Organization, Competitor, Region


class OrganizationSerializer(BaseModelSerializer):
    brands_count = serializers.SerializerMethodField()
    
    class Meta(BaseModelSerializer.Meta):
        model = Organization
        fields = BaseModelSerializer.Meta.fields + (
            'name', 'description', 'status', 'brands_count',
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ('brands_count',)
    
    def get_brands_count(self, obj):
        return obj.brand_set.alive().count()
    
    def validate_name(self, value):
        qs = Organization.objects.alive().filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Organization with this name already exists.")
        return value


class CompetitorSerializer(BaseModelSerializer):
    class Meta:
        model = Competitor
        fields = ('id', 'created_at', 'updated_at', 'region', 'name', 'description')
        read_only_fields = ('id', 'created_at', 'updated_at')


class BrandSerializer(BaseModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta(BaseModelSerializer.Meta):
        model = Brand
        fields = BaseModelSerializer.Meta.fields + (
            "name", "code", "description",
            "organization", "organization_name",
            "category", "category_name",
            "is_active", "logo",
        )
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ("is_active", "organization_name", "category_name")

    def validate_name(self, value):
        """
        Ensure uniqueness of brand name (case-insensitive),
        but allow the current instance to keep its name when editing.
        """
        qs = Brand.objects.alive().filter(name__iexact=value)
        if self.instance:  # editing
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Brand with this name already exists.")
        return value

class RegionSerializer(BaseModelSerializer):
    brand_name = serializers.CharField(source='brand.name', read_only=True)

    class Meta(BaseModelSerializer.Meta):
        model = Region
        fields = BaseModelSerializer.Meta.fields + ('name', 'code', 'brand', 'brand_name')
        read_only_fields = BaseModelSerializer.Meta.read_only_fields + ('brand_name',)
