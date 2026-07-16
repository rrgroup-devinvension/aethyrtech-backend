from rest_framework import serializers

class BaseModelSerializer(serializers.ModelSerializer):
    """Base ModelSerializer that handles read-only timestamp fields automatically."""
    class Meta:
        fields = ('id', 'created_at', 'updated_at', 'is_deleted')
        read_only_fields = ('id', 'created_at', 'updated_at')
