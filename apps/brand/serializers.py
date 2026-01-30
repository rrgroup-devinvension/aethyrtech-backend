from rest_framework import serializers
from core.serializers import BaseSerializer
from .models import Brand, Organization, Competitor


class OrganizationSerializer(BaseSerializer):
    brands_count = serializers.SerializerMethodField()
    
    class Meta(BaseSerializer.Meta):
        model = Organization
        fields = (
            'id', 'name', 'description', 'status', 'brands_count',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        )
        read_only_fields = ('created_by', 'updated_by', 'brands_count')
    
    def get_brands_count(self, obj):
        return obj.brands.filter(is_deleted=False).count()
    
    def validate_name(self, value):
        qs = Organization.objects.filter(name__iexact=value, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Organization with this name already exists.")
        return value


class CompetitorSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = Competitor
        fields = ('id', 'brand', 'name', 'description', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')


class BrandSerializer(BaseSerializer):
    platform_type = serializers.SerializerMethodField()
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    competitors = CompetitorSerializer(many=True, read_only=True)
    competitors_count = serializers.SerializerMethodField()
    
    class Meta(BaseSerializer.Meta):
        model = Brand
        fields = (
            "id", "name", "description",
            "organization", "organization_name",
            "category", "category_name",
            "platform_type",
            "is_active", "is_deleted",
            "competitors", "competitors_count",
            "created_at", "updated_at", "created_by", "updated_by",
        )
        read_only_fields = ("created_by", "updated_by", "is_active", "organization_name", "category_name", "competitors", "competitors_count")
    
    def get_competitors_count(self, obj):
        return obj.competitors.filter(is_deleted=False).count()

    def get_platform_type(self, obj):
        try:
            if obj.category and getattr(obj.category, 'platform_type', None):
                return obj.category.platform_type
        except Exception:
            pass
        return []

    def validate_name(self, value):
        """
        Ensure uniqueness of brand name (case-insensitive),
        but allow the current instance to keep its name when editing.
        """
        qs = Brand.objects.filter(name__iexact=value, is_deleted=False)
        if self.instance:  # editing
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Brand with this name already exists.")
        return value

