from rest_framework import serializers
from core.serializers import BaseSerializer
from .models import Brand

class BrandSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = Brand
        fields = ("id", "name", "logo", "description", "is_deleted", "created_at", "updated_at", "created_by", "updated_by")
        read_only_fields = ("created_by", "updated_by")

    def validate_name(self, value):
        if Brand.objects.filter(name__iexact=value, is_deleted=False).exists():
            raise serializers.ValidationError("Brand with this name already exists.")
        return value
