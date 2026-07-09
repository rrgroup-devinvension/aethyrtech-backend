from rest_framework import status
from rest_framework.response import Response
from core.views import BaseViewSet
from .models import Platform
from .serializers import PlatformSerializer

class PlatformViewSet(BaseViewSet):
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    search_fields = ('name', 'value', 'platform_type')
    ordering_fields = ('name', 'status', 'created_at', 'updated_at')
