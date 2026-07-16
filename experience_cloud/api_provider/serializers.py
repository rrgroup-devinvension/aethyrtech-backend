from shared.base.serializers import BaseModelSerializer
from .models import ApiProvider

class ApiProviderSerializer(BaseModelSerializer):
    class Meta(BaseModelSerializer.Meta):
        model = ApiProvider
        fields = BaseModelSerializer.Meta.fields + (
            'name', 'base_url', 'headers', 'authentication', 'status'
        )
