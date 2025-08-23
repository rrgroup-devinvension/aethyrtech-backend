from typing import Any, Dict, Iterable, Optional

from django.db.models import QuerySet
from rest_framework import viewsets, mixins, status, filters
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import action

from core.pagination import DefaultPageNumberPagination


class ReadOnlyBaseViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    """
    Read-only base with search & ordering enabled by default.
    """
    pagination_class = DefaultPageNumberPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields: Iterable[str] = ()
    ordering_fields: Iterable[str] = ("-created_at", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self) -> QuerySet:
        assert hasattr(self, "queryset"), "Define .queryset or override .get_queryset()"
        return self.queryset


class BaseViewSet(mixins.CreateModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  mixins.DestroyModelMixin,
                  mixins.ListModelMixin,
                  viewsets.GenericViewSet):
    """
    - CRUD with search, ordering, pagination
    - Bulk delete action
    - Safe default ordering
    """
    pagination_class = DefaultPageNumberPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields: Iterable[str] = ()
    ordering_fields: Iterable[str] = ("-created_at", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_queryset(self) -> QuerySet:
        assert hasattr(self, "queryset"), "Define .queryset or override .get_queryset()"
        return self.queryset

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request: Request, *args, **kwargs) -> Response:
        """
        Accepts: {"ids": ["uuid1", "uuid2", ...]}
        Uses model's delete() – so compatible with SoftDeleteModel.
        """
        ids = request.data.get("ids") or []
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "Provide a non-empty list of ids."},
                            status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(id__in=ids)
        count = qs.count()
        for obj in qs:
            obj.delete()
        return Response({"deleted": count}, status=status.HTTP_200_OK)
