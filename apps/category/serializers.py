from rest_framework import serializers
from core.serializers import BaseSerializer
from .models import Category, CategoryPincode, CategoryKeyword


class CategoryKeywordSerializer(BaseSerializer):
    platform = serializers.CharField(required=True)
    class Meta(BaseSerializer.Meta):
        model = CategoryKeyword
        fields = ( 'id', 'category', 'keyword', 'platform', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class CategoryPincodeSerializer(BaseSerializer):
    class Meta(BaseSerializer.Meta):
        model = CategoryPincode
        fields = ('id', 'category', 'pincode', 'city', 'state', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class CategorySerializer(BaseSerializer):
    pincodes_count = serializers.SerializerMethodField()
    keywords_count = serializers.SerializerMethodField()
    class Meta(BaseSerializer.Meta):
        model = Category
        fields = ( 'id', 'name', 'platform_type', 'description', 'status', 'pincodes_count', 'keywords_count', 'created_at', 'updated_at', 'created_by', 'updated_by')
        read_only_fields = ( 'created_by', 'updated_by', 'pincodes_count', 'keywords_count')
    def get_pincodes_count(self, obj):
        return obj.category_pincodes.count()
    def get_keywords_count(self, obj):
        request = self.context.get('request')
        platform = None
        if request:
            platform = request.query_params.get('platform')
        qs = obj.category_keywords.all()
        if platform:
            qs = qs.filter(platform=platform)
        return qs.count()
    def validate_name(self, value):
        qs = Category.objects.filter(name__iexact=value, is_deleted=False)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Category with this name already exists.")
        return value


class CategoryDetailSerializer(CategorySerializer):
    pincodes = CategoryPincodeSerializer(source='category_pincodes',many=True,read_only=True)
    keywords = CategoryKeywordSerializer(source='category_keywords',many=True,read_only=True)
    class Meta(CategorySerializer.Meta):
        fields = CategorySerializer.Meta.fields + ('pincodes', 'keywords')
