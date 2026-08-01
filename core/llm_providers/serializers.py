from shared.base.serializers import BaseModelSerializer

from .models import LLMProvider


class LLMProviderSerializer(BaseModelSerializer):
    """Serializer for the LLMProvider model.

    Handles the serialization of provider configurations, ensuring that
    sensitive data (like the decrypted API key) is handled securely and
    properly formatted for API responses.
    """
    class Meta(BaseModelSerializer.Meta):
        model = LLMProvider
        fields = (
            'id', 'created_at', 'updated_at',
            'name', 'enabled', 'is_default', 'api_key', 'model',
            'base_url', 'description', 'timeout_seconds', 'max_retries',
            'health_check_path', 'health_check_status', 'last_health_check'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
