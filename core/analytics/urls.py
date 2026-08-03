from django.urls import path
from typing import Any
from .views import DashboardDataView

urlpatterns: list[Any] = [
    path('dashboard/', DashboardDataView.as_view(), name='core_dashboard'),
]
