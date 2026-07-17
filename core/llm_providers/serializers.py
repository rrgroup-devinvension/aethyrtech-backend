from rest_framework import serializers
from .models import LLMProvider

class LLMProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMProvider
        fields = (
            'id', 'created_at', 'updated_at',
            'name', 'enabled', 'api_key', 'model',
            'base_url', 'description', 'timeout_seconds', 'max_retries',
            'health_check_path', 'health_check_status', 'last_health_check'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
