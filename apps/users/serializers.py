from rest_framework import serializers
from .models import User
from apps.brand.models import Brand
from apps.brand.serializers import BrandSerializer

class UserSerializer(serializers.ModelSerializer):
    brands = BrandSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = ("id", "name", "email", "role", "brands", "created_at", "updated_at", "created_by", "updated_by")
        read_only_fields = ("created_by", "updated_by")

class UserCreateUpdateSerializer(serializers.ModelSerializer):
    # accept "brands" as a list of IDs
    brands = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Brand.objects.all(),
        write_only=True,
        required=False
    )

    class Meta:
        model = User
        fields = ("name", "email", "role", "brands", "password")
        extra_kwargs = {
            "password": {"write_only": True, "required": False}
        }

    def create(self, validated_data):
        brands = validated_data.pop("brands", [])
        password = validated_data.pop("password", None)

        user = User.objects.create(**validated_data)

        if password:
            user.set_password(password)
            user.save()

        if brands:
            user.brands.set(brands)

        return user

    def update(self, instance, validated_data):
        brands = validated_data.pop("brands", None)
        validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if brands is not None:
            instance.brands.set(brands)

        return instance

class PasswordUpdateSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)
