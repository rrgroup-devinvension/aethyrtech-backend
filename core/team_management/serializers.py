from rest_framework import serializers
from .models import TeamMember
from core.organizations.models import Brand

class TeamMemberSerializer(serializers.ModelSerializer):
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all())

    class Meta:
        model = TeamMember
        fields = ['id', 'brand', 'name', 'role', 'email', 'mobile', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
