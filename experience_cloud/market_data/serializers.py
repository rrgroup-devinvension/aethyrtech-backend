from rest_framework import serializers
from experience_cloud.market_integrations.models.xbytes import XBytesProduct

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = XBytesProduct
        fields = '__all__'
