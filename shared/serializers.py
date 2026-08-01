
from rest_framework import serializers


class EmptySerializer(serializers.Serializer):
    """An empty serializer used for endpoints that do not require any input body."""
    pass
