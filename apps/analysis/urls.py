from django.urls import path
from django.urls import path
from .views import (
    DashboardDataView,
    BrandDashboardDataView,
    CategoryViewDataView,
    BrandAuditDataView,
    ProductCatalogDataView,
    CatalogDetailView,
    ReportsDataView,
    ContentInsightsDataView,
    GenerateContentView,
    UpdateProductContentView
)

urlpatterns = [
    path("dashboard/", DashboardDataView.as_view(), name="dashboard_data_view"),
    path("brand-dashboard/<int:brand_id>/", BrandDashboardDataView.as_view(), name="brand_dashboard_data_view"),
    path("category-view/<int:brand_id>/", CategoryViewDataView.as_view(), name="category_view_data_view"),
    path("brand-audit/<int:brand_id>/", BrandAuditDataView.as_view(), name="brand_audit_data_view"),
    path("product-catalog/<int:brand_id>/", ProductCatalogDataView.as_view(), name="product_catalog_data_view"),
    path("catalog-detail/<int:brand_id>/<str:product_id>/", CatalogDetailView.as_view(), name="catalog_detail_view"),
    path("reports/<int:brand_id>/", ReportsDataView.as_view(), name="reports_data_view"),
    path("content-insights/<int:brand_id>/", ContentInsightsDataView.as_view(), name="content_insights_data_view"),
    path("generate-content/", GenerateContentView.as_view()),
    path("update-product-content/", UpdateProductContentView.as_view()),
]