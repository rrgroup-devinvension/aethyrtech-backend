from rest_framework import serializers

from shared.base.serializers import BaseModelSerializer

from .models import Category


class CategorySerializer(BaseModelSerializer):
    """Serializer for the Category model.

    Handles serialization of core category fields and provides
    custom validation logic to ensure category names remain unique.
    """
    class Meta(BaseModelSerializer.Meta):
        model = Category
        fields: tuple[str, ...] = ('id', 'name', 'description', 'status', 'created_at', 'updated_at')
        read_only_fields: tuple[str, ...] = ('id', 'created_at', 'updated_at')

    def validate_name(self, value):
        """Validate that the provided category name is case-insensitively unique.

        Excludes the current instance from the uniqueness check if this is an update operation.
        """
        qs = Category.objects.filter(name__iexact=value)

        # self.instance can theoretically be a list if many=True, so we verify it's a single Category object
        if isinstance(self.instance, Category):
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise serializers.ValidationError("Category with this name already exists.")
        return value


class CategoryDetailSerializer(CategorySerializer):
    """Detailed serializer for the Category model.

    Inherits from the base CategorySerializer. Typically used for retrieving
    a specific category, potentially with expanded relational data in the future.
    """
    class Meta(CategorySerializer.Meta):
        fields: tuple[str, ...] = CategorySerializer.Meta.fields


