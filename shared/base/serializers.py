from rest_framework import serializers

class BaseModelSerializer(serializers.ModelSerializer):
    """Base ModelSerializer that handles read-only timestamp fields automatically."""
    pass
