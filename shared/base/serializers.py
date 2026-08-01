from typing import Any

from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """Base ModelSerializer that handles read-only timestamp fields automatically."""
    class Meta:  # type: ignore
        fields: Any = ('id', 'created_at', 'updated_at', 'is_deleted')
        read_only_fields: Any = ('id', 'created_at', 'updated_at')
