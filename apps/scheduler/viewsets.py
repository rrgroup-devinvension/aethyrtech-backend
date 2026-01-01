"""
ViewSets for Pincode and Keyword CRUD operations.
"""
from rest_framework import viewsets, filters
from core.views.base import BaseViewSet
from apps.scheduler.models import Pincode, Keyword
from apps.scheduler.serializers import PincodeSerializer, KeywordSerializer
from core.pagination import DefaultPageNumberPagination


class PincodeViewSet(BaseViewSet):
    """CRUD operations for Pincode model."""
    queryset = Pincode.objects.filter(is_deleted=False).order_by('-created_at')
    serializer_class = PincodeSerializer
    search_fields = ['pincode', 'city', 'state']
    ordering_fields = ['pincode', 'city', 'state', 'created_at', 'updated_at']
    ordering = ['-created_at']


class KeywordViewSet(BaseViewSet):
    """CRUD operations for Keyword model."""
    queryset = Keyword.objects.filter(is_deleted=False).select_related('pincode').order_by('-created_at')
    serializer_class = KeywordSerializer
    search_fields = ['keyword', 'pincode__pincode']
    ordering_fields = ['keyword', 'last_synced', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Override to add optional filtering by pincode ID."""
        queryset = super().get_queryset()
        pincode_id = self.request.query_params.get('pincode_id')
        if pincode_id:
            queryset = queryset.filter(pincode_id=pincode_id)
        return queryset
