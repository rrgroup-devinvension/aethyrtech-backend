from django.urls import path
from .views import (
    catalog_data_view,
    report_data_view,
    summary_data_view,
    reports_data_tree_view
)

urlpatterns = [
    path('catalog/', catalog_data_view, name='catalog_data_view'),
    path('report/', report_data_view, name='report_data_view'),
    path('summary/', summary_data_view, name='summary_data_view'),
    path('reports-tree/', reports_data_tree_view, name='reports_data_tree_view'),
]
