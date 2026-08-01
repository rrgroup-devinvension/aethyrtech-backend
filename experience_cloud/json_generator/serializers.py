from rest_framework import serializers

from shared.base.serializers import BaseModelSerializer

from .models import JsonTemplate, RegionJsonFile


class JsonTemplateSerializer(BaseModelSerializer):
    """Serializer for managing JSON/CSV payload configuration templates."""
    class Meta(BaseModelSerializer.Meta):
        model = JsonTemplate
        fields = ('id', 'name', 'template', 'process_type', 'format', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class RegionJsonFileSerializer(BaseModelSerializer):
    """Serializer for tracking and exposing Region-specific JSON payload generation statuses."""
    template_name = serializers.CharField(source='template.name', read_only=True)
    process_type = serializers.CharField(source='template.process_type', read_only=True)
    file_path = serializers.SerializerMethodField()

    def get_file_path(self, obj):
        """Build and return the absolute URL path for the generated payload file."""
        if obj.file_path:
            from django.conf import settings

            # Remove leading slash from file_path if exists to prevent double slash
            clean_path = obj.file_path.lstrip('/')

            # Base media path
            if obj.file_path.startswith(settings.MEDIA_URL) or obj.file_path.startswith('/media/'):
                path = obj.file_path
            else:
                path = f"{settings.MEDIA_URL}{clean_path}"

            # Build absolute URI (e.g., http://localhost:8000/media/...)
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(path)
            return path
        return None

    class Meta(BaseModelSerializer.Meta):
        model = RegionJsonFile
        fields = (
            'id', 'region', 'template', 'template_name', 'process_type',
            'file_name', 'file_path', 'file_size', 'checksum',
            'generation_duration', 'products_processed', 'last_generated_at', 'task_id',
            'status', 'error_message',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'template_name', 'process_type')
