from typing import ClassVar

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated

from core.authentication.permissions import AppPermissions
from shared.base.views import BaseViewSet

from .models import TeamMember
from .serializers import TeamMemberSerializer


class TeamMemberViewSet(BaseViewSet):
    """ViewSet for CRUD operations on TeamMember.

    Allows filtering by brand ID.
    Enforces tenant isolation via organization_field.
    """
    queryset = TeamMember.objects.all().order_by('-created_at')
    serializer_class = TeamMemberSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('brand',)
    organization_field = 'brand__organization'

    permission_mapping: ClassVar[dict[str, str]] = {
        'GET': AppPermissions.READ_TEAM_MEMBER,
        'POST': AppPermissions.CREATE_TEAM_MEMBER,
        'PUT': AppPermissions.UPDATE_TEAM_MEMBER,
        'PATCH': AppPermissions.UPDATE_TEAM_MEMBER,
        'DELETE': AppPermissions.DELETE_TEAM_MEMBER
    }

