from rest_framework import serializers
from .models import ApiProvider

class ApiProviderSerializer(serializers.ModelSerializer):
    class Meta:
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
