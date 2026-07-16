from shared.base.serializers import BaseModelSerializer
from .models import LLMProvider

class LLMProviderSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = LLMProvider
        fields = BaseModelSerializer.Meta.fields + (
            'name', 'enabled', 'api_key', 'model'
        )
