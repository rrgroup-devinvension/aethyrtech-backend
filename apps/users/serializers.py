from rest_framework import serializers
from .models import User
from apps.brand.serializers import BrandSerializer

class UserSerializer(serializers.ModelSerializer):
    brands = BrandSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "brands", "created_at", "updated_at", "created_by", "updated_by")
        read_only_fields = ("created_by", "updated_by")

class UserCreateUpdateSerializer(serializers.ModelSerializer):
    brand_ids = serializers.ListField(write_only=True, required=False, child=serializers.IntegerField())

    class Meta:
        model = User
        fields = ("name", "email", "role", "brand_ids", "password")

    def create(self, validated_data):
        brand_ids = validated_data.pop("brand_ids", [])
        password = validated_data.pop("password", None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        if brand_ids:
            user.brands.set(brand_ids)
        return user

    def update(self, instance, validated_data):
        brand_ids = validated_data.pop("brand_ids", None)
        password = validated_data.pop("password", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        if brand_ids is not None:
            instance.brands.set(brand_ids)
        return instance
