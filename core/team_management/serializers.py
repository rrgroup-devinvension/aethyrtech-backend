from rest_framework import serializers

from core.organizations.models import Brand
from shared.base.serializers import BaseModelSerializer

from .models import TeamMember


class TeamMemberSerializer(BaseModelSerializer):
    """Team member serializer."""
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())

    class Meta(BaseModelSerializer.Meta):
        model = TeamMember
        fields = ('id', 'brand', 'name', 'role', 'email', 'mobile', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
