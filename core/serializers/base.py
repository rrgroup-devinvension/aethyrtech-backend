from typing import Iterable, Optional
from rest_framework import serializers


class DynamicFieldsMixin:
    """
    Allow ?fields=a,b,c or serializer(fields=('a','b')) to limit returned fields.
    """
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        request = getattr(getattr(self, "context", None), "get", lambda *_: None)("request")
        if request:
            param_fields = request.query_params.get("fields")
            if param_fields:
                fields = [f.strip() for f in param_fields.split(",") if f.strip()]

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name, None)


class WritableReadOnlyFieldsMixin:
    """Treat read_only fields as writable on create/update if explicitly allowed via `writable_read_only = True`."""
    writable_read_only: bool = False

    def get_fields(self):
        fields = super().get_fields()
        if getattr(self, "writable_read_only", False):
            for f in fields.values():
                if getattr(f, "read_only", False):
                    f.read_only = False
        return fields


class BaseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    """
    - Provides DynamicFields.
    - Uniform datetime formatting (override in settings if desired).
    """
    class Meta:
        extra_kwargs = {
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
            "id": {"read_only": True},
        }
