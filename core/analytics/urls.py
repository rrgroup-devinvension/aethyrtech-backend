from typing import Any

from django.urls import path

from .views import DashboardDataView

urlpatterns: list[Any] = [
    path('dashboard/', DashboardDataView.as_view(), name='core_dashboard'),
]
