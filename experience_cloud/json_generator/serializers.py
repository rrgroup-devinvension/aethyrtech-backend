from rest_framework import serializers

from shared.base.serializers import BaseModelSerializer

from .models import JsonTemplate, RegionJsonFile, TemplateCodes

VALID_TEMPLATE_CODES = [{"id": choice[0], "name": choice[1]} for choice in TemplateCodes.choices]


class JsonTemplateSerializer(BaseModelSerializer):
    """Serializer for managing JSON/CSV payload configuration templates."""
    class Meta(BaseModelSerializer.Meta):
        model = JsonTemplate
        fields = ('id', 'name', 'template', 'file_name', 'parent_folder', 'parent_template', 'process_type', 'file_format', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_template(self, value):
        valid_ids = [item['id'] for item in VALID_TEMPLATE_CODES]
        if value not in valid_ids:
            raise serializers.ValidationError(f"Invalid template code. Must be one of: {', '.join(valid_ids)}")
        return value

    def validate_file_format(self, value):
        from .models import FormatCodes
        valid_formats = [choice[0] for choice in FormatCodes.choices]
        if value not in valid_formats:
            raise serializers.ValidationError(f"Invalid file format. Must be one of: {', '.join(valid_formats)}")
        return value


class RegionJsonFileSerializer(BaseModelSerializer):
    """Serializer for tracking and exposing Region-specific JSON payload generation statuses."""
    template_name = serializers.CharField(source='template.name', read_only=True)
    template_code = serializers.CharField(source='template.template', read_only=True)
    process_type = serializers.CharField(source='template.process_type', read_only=True)
    parent_template = serializers.IntegerField(source='template.parent_template_id', read_only=True)
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
            'id', 'region', 'template', 'template_name', 'template_code', 'process_type', 'parent_template',
            'file_name', 'file_path', 'file_size', 'checksum',
            'generation_duration', 'products_processed', 'last_generated_at', 'task_id',
            'status', 'error_message',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'template_name', 'template_code', 'process_type', 'parent_template')
