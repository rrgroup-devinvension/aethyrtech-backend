from experience_cloud.market_integrations.models.xbytes import XBytesProduct
from shared.base.serializers import BaseModelSerializer


class ProductSerializer(BaseModelSerializer):
    """Serialize XBytes secondary database product models.

    Maps all product model attributes, including pricing, availability, and media URIs,
    into a standardized JSON structure for API consumption and frontend rendering.
    """
    class Meta(BaseModelSerializer.Meta):
        model = XBytesProduct
        fields = '__all__'
