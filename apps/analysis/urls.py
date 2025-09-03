from django.urls import path
from django.urls import path
from .views import (
    DashboardDataView,
    BrandDashboardDataView,
    CategoryViewDataView,
    BrandAuditDataView,
    ProductCatalogDataView,
    ReportTreeDataView,
    ContentInsightsDataView,
)

urlpatterns = [
    path("dashboard/", DashboardDataView.as_view(), name="dashboard_data_view"),
    path("brand-dashboard/<int:brand_id>/", BrandDashboardDataView.as_view(), name="brand_dashboard_data_view"),
    path("category-view/<int:brand_id>/", CategoryViewDataView.as_view(), name="category_view_data_view"),
    path("brand-audit/<int:brand_id>/", BrandAuditDataView.as_view(), name="brand_audit_data_view"),
    path("product-catalog/<int:brand_id>/", ProductCatalogDataView.as_view(), name="product_catalog_data_view"),
    path("report-tree/<int:brand_id>/", ReportTreeDataView.as_view(), name="report_tree_data_view"),
    path("content-insights/<int:brand_id>/", ContentInsightsDataView.as_view(), name="content_insights_data_view"),
]