from experience_cloud.market_integrations.models.xbytes import XBytesProduct
from shared.base.serializers import BaseModelSerializer

from .models import DataImportJob


class ProductSerializer(BaseModelSerializer):
    """Serialize XBytes secondary database product models.

    Maps all product model attributes, including pricing, availability, and media URIs,
    into a standardized JSON structure for API consumption and frontend rendering.
    """
    class Meta(BaseModelSerializer.Meta):
        model = XBytesProduct
        fields = '__all__'


class DataImportJobSerializer(BaseModelSerializer):
    """Serialize the Data Import Job status and details."""
    class Meta(BaseModelSerializer.Meta):
        model = DataImportJob
        fields = '__all__'

