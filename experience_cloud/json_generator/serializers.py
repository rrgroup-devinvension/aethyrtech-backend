from rest_framework import serializers
from .models import JsonTemplate, RegionJsonFile
from shared.base.serializers import BaseModelSerializer
from experience_cloud.executions.serializers import JsonFileTaskSerializer

class JsonTemplateSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = JsonTemplate
        fields = ('id', 'name', 'template', 'process_type', 'format', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class RegionJsonFileSerializer(BaseModelSerializer):
    task = JsonFileTaskSerializer(read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta(BaseModelSerializer.Meta):
        model = RegionJsonFile
        fields = (
            'id', 'region', 'template', 'template_name', 
            'file_name', 'file_path', 'file_size', 'checksum', 
            'generation_duration', 'last_generated_at', 'task',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'task', 'template_name')
