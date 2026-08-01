from typing import Any

from rest_framework import serializers

from core.categories.models import Category
from shared.base.serializers import BaseModelSerializer

from .models import Keyword, Location, Platform


class PlatformSerializer(BaseModelSerializer):
    """Serializer for mapping Platform model instances to JSON representations."""
    api_provider_name = serializers.CharField(source='api_provider.name', read_only=True, allow_null=True)

    class Meta(BaseModelSerializer.Meta):
        model = Platform
        fields = (
            'id', 'created_at', 'updated_at',
            'name', 'code', 'platform_type', 'api_provider', 'api_provider_name', 'configuration', 'status'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

class LocationSerializer(BaseModelSerializer):
    """Serializer for mapping Location model instances to JSON representations."""
    region_name = serializers.CharField(source='region.name', read_only=True, allow_null=True)
    platform_name = serializers.CharField(source='platform.name', read_only=True, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    category: Any = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = Location
        fields = (
            'id', 'created_at', 'updated_at',
            'pincode', 'address', 'lat', 'lng', 'region', 'region_name',
            'platform', 'platform_name', 'category', 'category_name', 'is_active'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        """Validate location data."""
        pincode = data.get('pincode', '')
        address = data.get('address', '')

        if not pincode and not address:
            raise serializers.ValidationError({"non_field_errors": ["Either pincode or address must be provided."]})

        if not pincode:
            data['pincode'] = ''

        region = data.get('region')
        if not data.get('category') and region and getattr(region, 'brand', None):
            data['category'] = getattr(region.brand, 'category', None)

        return super().validate(data)

class KeywordSerializer(BaseModelSerializer):
    """Serializer for mapping Keyword model instances to JSON representations."""
    region_name = serializers.CharField(source='region.name', read_only=True, allow_null=True)
    platform_name = serializers.CharField(source='platform.name', read_only=True, allow_null=True)
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    category: Any = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), required=False, allow_null=True
    )

    class Meta(BaseModelSerializer.Meta):
        model = Keyword
        fields = (
            'id', 'created_at', 'updated_at',
            'keyword', 'category', 'category_name', 'region', 'region_name',
            'platform', 'platform_name', 'display_order', 'is_active'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, data):
        """Validate keyword data."""
        region = data.get('region')
        if not data.get('category') and region and getattr(region, 'brand', None):
            data['category'] = getattr(region.brand, 'category', None)
        return super().validate(data)
