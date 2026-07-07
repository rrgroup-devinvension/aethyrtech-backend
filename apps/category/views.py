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
        page = self.paginate_queryset(pincodes)
        if page is not None:
            serializer = CategoryPincodeSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
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

            # Add or update associations
            current_dict = {cp.pincode: cp for cp in current_assocs}
            to_create = []
            to_update = []
            
            for pincode_value in to_add:
                pincode_data = csv_map.get(pincode_value, {})
                to_create.append(CategoryPincode(
                    category=category,
                    pincode=pincode_value,
                    city=pincode_data.get('city', ''),
                    state=pincode_data.get('state', '')
                ))

            # Update existing if city or state changes
            for pincode_value, pincode_data in csv_map.items():
                if pincode_value in current_dict:
                    cp = current_dict[pincode_value]
                    new_city = pincode_data.get('city', '')
                    new_state = pincode_data.get('state', '')
                    if cp.city != new_city or cp.state != new_state:
                        cp.city = new_city
                        cp.state = new_state
                        to_update.append(cp)

            if to_create:
                try:
                    CategoryPincode.objects.bulk_create(to_create, ignore_conflicts=True)
                    added_count = len(to_create)
                except Exception as e:
                    errors.append(f"Bulk create failed: {str(e)}")
                    
            if to_update:
                try:
                    CategoryPincode.objects.bulk_update(to_update, fields=['city', 'state'])
                except Exception as e:
                    errors.append(f"Bulk update failed: {str(e)}")

            # Remove associations not present in CSV
            if to_remove:
                try:
                    deleted_count, _ = CategoryPincode.objects.filter(category=category, pincode__in=to_remove).delete()
                    removed_count = deleted_count
                except Exception as e:
                    errors.append(f"Bulk delete failed: {str(e)}")

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
        # order by the 'order' field then creation time
        keywords = keywords.order_by('order', 'created_at')
        
        page = self.paginate_queryset(keywords)
        if page is not None:
            serializer = CategoryKeywordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = CategoryKeywordSerializer(keywords, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='keywords/remove-by-platform')
    def remove_keywords_by_platform(self, request, pk=None):
        """Remove all keywords for a given platform within this category."""
        category = self.get_object()
        platform = request.query_params.get('platform') or request.data.get('platform')
        if not platform:
            return Response({'detail': 'platform is required'}, status=status.HTTP_400_BAD_REQUEST)
        qs = CategoryKeyword.objects.filter(category=category, platform=platform)
        deleted_count, _ = qs.delete()
        return Response({'detail': f'{deleted_count} keywords removed for platform {platform}', 'deleted': deleted_count})

    @action(detail=True, methods=['delete'], url_path='keywords/clear')
    def clear_all_keywords(self, request, pk=None):
        """Remove all keywords associated with this category."""
        category = self.get_object()
        qs = CategoryKeyword.objects.filter(category=category)
        deleted_count, _ = qs.delete()
        return Response({'detail': f'{deleted_count} keywords removed', 'deleted': deleted_count})

    @action(detail=True, methods=['delete'], url_path='pincodes/clear')
    def clear_all_pincodes(self, request, pk=None):
        """Remove all pincodes associated with this category."""
        category = self.get_object()
        qs = CategoryPincode.objects.filter(category=category)
        deleted_count, _ = qs.delete()
        return Response({'detail': f'{deleted_count} pincodes removed', 'deleted': deleted_count})

    @action(detail=True, methods=['post'], url_path='keywords/add')
    def add_keyword(self, request, pk=None):
        category = self.get_object()
        keyword = request.data.get('keyword', '').strip()
        platform = request.data.get('platform', '').strip()
        order = request.data.get('order', None)
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
        # update order if provided
        try:
            if order is not None:
                try:
                    obj.order = int(order)
                except (ValueError, TypeError):
                    obj.order = 0
                obj.save()
        except Exception:
            pass
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
            current_keywords = CategoryKeyword.objects.filter(category=category)
            current_dict = {(kw.keyword, kw.platform): kw for kw in current_keywords}
            
            to_create = []
            to_update = []
            seen_in_csv = set()
            
            for row in csv_reader:
                keyword = row.get('keyword', '').strip()
                platform = row.get('platform', '').strip()
                order_val = row.get('order', '').strip() if row.get('order') is not None else ''
                
                if not keyword or not platform:
                    skipped_count += 1
                    continue
                    
                key = (keyword, platform)
                if key in seen_in_csv:
                    skipped_count += 1
                    continue
                seen_in_csv.add(key)
                
                order_int = 0
                if order_val != '':
                    try:
                        order_int = int(order_val)
                    except ValueError:
                        order_int = 0
                        
                if key in current_dict:
                    obj = current_dict[key]
                    if order_val != '' and obj.order != order_int:
                        obj.order = order_int
                        to_update.append(obj)
                    else:
                        skipped_count += 1
                else:
                    to_create.append(CategoryKeyword(
                        category=category,
                        keyword=keyword,
                        platform=platform,
                        order=order_int
                    ))
                    
            if to_create:
                try:
                    CategoryKeyword.objects.bulk_create(to_create, ignore_conflicts=True)
                    added_count = len(to_create)
                except Exception as e:
                    errors.append(f"Bulk create failed: {str(e)}")
                    
            if to_update:
                try:
                    CategoryKeyword.objects.bulk_update(to_update, fields=['order'])
                except Exception as e:
                    errors.append(f"Bulk update failed: {str(e)}")
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
