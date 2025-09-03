from rest_framework import serializers
from core.serializers import BaseSerializer
from .models import Brand

class BrandSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = Brand
        fields = (
            "id",
            "name",
            "logo",
            "description",
            "is_active",
            "is_deleted",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )
        read_only_fields = ("created_by", "updated_by")

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