from shared.base.serializers import BaseModelSerializer

from .models import ApiProvider


class ApiProviderSerializer(BaseModelSerializer):
    """Serializer for mapping ApiProvider model instances to JSON representations."""
    class Meta(BaseModelSerializer.Meta):
        model = ApiProvider
        fields = (
            'id', 'created_at', 'updated_at',
            'name', 'code', 'base_url', 'api_version', 'auth_type', 'default_headers',
            'credentials', 'timeout', 'retry_count', 'retry_delay',
            'health_check_path', 'test_http_method', 'test_payload',
            'status', 'health_check_status', 'last_health_check',
            'description'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_code(self, value):
        """Validate that the code is a valid choice in ApiProviderCodes."""
        from .models import ApiProviderCodes
        valid_codes = [choice.value for choice in ApiProviderCodes]
        if value and value not in valid_codes:
            from rest_framework import serializers
            raise serializers.ValidationError(f"Invalid code '{value}'. Valid options are: {', '.join(valid_codes)}")
        return value
