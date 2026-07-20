from core.authentication.permissions import AppPermissions
from rest_framework import status
from rest_framework.response import Response
from shared.base.views import BaseViewSet
from .models import Platform
from .serializers import PlatformSerializer

class PlatformViewSet(BaseViewSet):
    action_permission_mapping = {
        'upload-file': AppPermissions.MANAGE_TAXONOMY,
        'export-data': AppPermissions.READ_PLATFORMS,
        'download-template': AppPermissions.READ_PLATFORMS,
        'bulk-delete': AppPermissions.MANAGE_TAXONOMY,
    }

    organization_field = None
    permission_mapping = {
        'GET': AppPermissions.READ_PLATFORMS,
        'POST': None,
        'PUT': None,
        'PATCH': None,
        'DELETE': None
    }
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    search_fields = ('name', 'value', 'platform_type')
    ordering_fields = ('name', 'status', 'created_at', 'updated_at')
