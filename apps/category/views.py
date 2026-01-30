import csv
import io
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from core.views import BaseViewSet
from .models import Category, CategoryPincode, CategoryKeyword
from .serializers import (
    CategorySerializer, CategoryDetailSerializer,
    CategoryPincodeSerializer, CategoryKeywordSerializer
)


class CategoryViewSet(BaseViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ('name', 'description')
    ordering_fields = ('name', 'status', 'created_at', 'updated_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=True, methods=['get'], url_path='pincodes')
    def list_pincodes(self, request, pk=None):
        category = self.get_object()
        pincodes = category.category_pincodes.all()
        # page = self.paginate_queryset(pincodes)
        # if page is not None:
        #     serializer = CategoryPincodeSerializer(page, many=True)
        #     return self.get_paginated_response(serializer.data)
        serializer = CategoryPincodeSerializer(pincodes, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='pincodes/add')
    def add_pincode(self, request, pk=None):
        category = self.get_object()
        pincode_value = request.data.get('pincode_value', '').strip()
        city = request.data.get('city', '').strip()
        state = request.data.get('state', '').strip()
        
        if not pincode_value:
            return Response(
                {'detail': 'pincode_value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get or create the category-pincode association
        obj, created = CategoryPincode.objects.get_or_create(
            category=category,
            pincode=pincode_value,
            defaults={'city': city, 'state': state}
        )
        
        # Update city/state if provided and exists
        if not created and (city or state):
            if city:
                obj.city = city
            if state:
                obj.state = state
            obj.save()
        
        serializer = CategoryPincodeSerializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='pincodes/upload-csv')
    def upload_pincodes_csv(self, request, pk=None):
        category = self.get_object()
        csv_file = request.FILES.get('file')
        
        if not csv_file:
            return Response(
                {'detail': 'CSV file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            decoded_file = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))

            # Collect pincodes from CSV (unique)
            csv_pincodes = []
            for row in csv_reader:
                pincode_value = row.get('pincode', '').strip()
                city = row.get('city', '').strip()
                state = row.get('state', '').strip()
                if not pincode_value:
                    continue
                csv_pincodes.append({
                    'pincode': pincode_value,
                    'city': city,
                    'state': state
                })

            csv_set = {p['pincode'] for p in csv_pincodes}
            csv_map = {p['pincode']: p for p in csv_pincodes}

            added_count = 0
            removed_count = 0
            skipped_count = 0
            errors = []

            # Current pincodes associated with this category
            current_assocs = CategoryPincode.objects.filter(category=category)
            current_set = set([cp.pincode for cp in current_assocs])

            # Determine which to add and which to remove to synchronize
            to_add = csv_set - current_set
            to_remove = current_set - csv_set

            # Add new associations
            for pincode_value in to_add:
                pincode_data = csv_map.get(pincode_value, {})
                try:
                    obj, created = CategoryPincode.objects.get_or_create(
                        category=category,
                        pincode=pincode_value,
                        defaults={
                            'city': pincode_data.get('city', ''),
                            'state': pincode_data.get('state', '')
                        }
                    )
                    if created:
                        added_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    errors.append(f"Failed to add pincode {pincode_value}: {str(e)}")

            # Remove associations not present in CSV
            for pincode_value in to_remove:
                try:
                    cp = CategoryPincode.objects.get(category=category, pincode=pincode_value)
                    cp.delete()
                    removed_count += 1
                except CategoryPincode.DoesNotExist:
                    # already removed or inconsistent state
                    continue

            return Response({
                'detail': 'CSV sync processed successfully',
                'added': added_count,
                'removed': removed_count,
                'skipped': skipped_count,
                'errors': errors
            })
        except Exception as e:
            return Response(
                {'detail': f'Error processing CSV: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'], url_path='pincodes/remove/(?P<pincode_id>[^/.]+)')
    def remove_pincode(self, request, pk=None, pincode_id=None):
        category = self.get_object()
        try:
            category_pincode = CategoryPincode.objects.get(category=category, pincode=pincode_id)
            category_pincode.delete()
            return Response({'detail': 'Pincode association removed'}, status=status.HTTP_200_OK)
        except CategoryPincode.DoesNotExist:
            return Response(
                {'detail': 'Pincode association not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'], url_path='keywords')
    def list_keywords(self, request, pk=None):
        category = self.get_object()
        platform = request.query_params.get('platform')
        keywords = category.category_keywords.all()
        if platform:
            keywords = keywords.filter(platform=platform)
        serializer = CategoryKeywordSerializer(keywords, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='keywords/add')
    def add_keyword(self, request, pk=None):
        category = self.get_object()
        keyword = request.data.get('keyword', '').strip()
        platform = request.data.get('platform', '').strip()
        if not keyword:
            return Response(
                {'detail': 'keyword is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not platform:
            return Response(
                {'detail': 'platform is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        obj, created = CategoryKeyword.objects.get_or_create(
            category=category,
            keyword=keyword,
            platform=platform
        )
        serializer = CategoryKeywordSerializer(obj)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='keywords/upload-csv')
    def upload_keywords_csv(self, request, pk=None):
        category = self.get_object()
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response({'detail': 'CSV file is required'},status=status.HTTP_400_BAD_REQUEST)
        try:
            decoded_file = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_file))
            added_count = 0
            skipped_count = 0
            errors = []
            for row in csv_reader:
                keyword = row.get('keyword', '').strip()
                platform = row.get('platform', '').strip()
                if not keyword or not platform:
                    skipped_count += 1
                    continue
                try:
                    _, created = CategoryKeyword.objects.get_or_create( category=category, keyword=keyword, platform=platform)
                    if created:
                        added_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    errors.append(f"{keyword} - {platform}: {str(e)}")
            return Response({ 'detail': 'CSV processed successfully', 'added': added_count, 'skipped': skipped_count, 'errors': errors})
        except Exception as e:
            return Response( {'detail': f'Error processing CSV: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='keywords/remove/(?P<keyword_id>[^/.]+)')
    def remove_keyword(self, request, pk=None, keyword_id=None):
        category = self.get_object()
        platform = request.query_params.get('platform')
        try:
            filters = {'category': category,'id': keyword_id}
            if platform:
                filters['platform'] = platform
            keyword = CategoryKeyword.objects.get(**filters)
            keyword.delete()
            return Response( {'detail': 'Keyword removed'}, status=status.HTTP_200_OK)
        except CategoryKeyword.DoesNotExist:
            return Response( {'detail': 'Keyword not found'}, status=status.HTTP_404_NOT_FOUND)
