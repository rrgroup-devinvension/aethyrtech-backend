"""URL routing configuration for the Experience Cloud Analytics application."""

from django.urls import path

from .views import (
    BrandAuditDataView,
    CatalogDetailView,
    CategoryDataView,
    ContentInsightsDataView,
    CROBarriersDataView,
    DashboardDataView,
    DashboardPositiveDataView,
    GenerateContentView,
    IncentiveInsightsDataView,
    InsightsDataView,
    PdpInsightsDataView,
    PlpInsightsDataView,
    ProductCatalogDataView,
    RegionDashboardDataView,
    ReportsDataView,
    ReviewsInsightsDataView,
    UpdateProductContentView,
)

urlpatterns = [
    # Global dashboard
    path("dashboard/", DashboardDataView.as_view(), name="dashboard_data_view"),

    # Region-specific JSON data APIs
    path("region-dashboard/<int:region_id>/", RegionDashboardDataView.as_view(), name="region_dashboard_data_view"),
    path("insights/<int:region_id>/", InsightsDataView.as_view(), name="insights_data_view"),
    path(
        "dashboard-positive/<int:region_id>/",
        DashboardPositiveDataView.as_view(),
        name="dashboard_positive_data_view",
    ),
    path("cro-barriers/<int:region_id>/", CROBarriersDataView.as_view(), name="cro_barriers_data_view"),
    path("plp-insights/<int:region_id>/", PlpInsightsDataView.as_view(), name="plp_insights_data_view"),
    path(
        "incentive-insights/<int:region_id>/",
        IncentiveInsightsDataView.as_view(),
        name="incentive_insights_data_view",
    ),
    path("pdp-insights/<int:region_id>/", PdpInsightsDataView.as_view(), name="pdp_insights_data_view"),
    path("reviews-insights/<int:region_id>/", ReviewsInsightsDataView.as_view(), name="reviews_insights_data_view"),
    path("category/<int:region_id>/", CategoryDataView.as_view(), name="category_view_data_view"),
    path("brand-audit/<int:region_id>/", BrandAuditDataView.as_view(), name="brand_audit_data_view"),
    path("content-insights/<int:region_id>/", ContentInsightsDataView.as_view(), name="content_insights_data_view"),

    # Catalog Specific APIs
    path("product-catalog/<int:region_id>/", ProductCatalogDataView.as_view(), name="product_catalog_data_view"),
    path("catalog-detail/<int:region_id>/<str:product_id>/", CatalogDetailView.as_view(), name="catalog_detail_view"),
    path("reports/<int:region_id>/", ReportsDataView.as_view(), name="reports_data_view"),

    # Action APIs (POST)
    path("generate-content/", GenerateContentView.as_view(), name="generate_content_view"),
    path("update-product-content/", UpdateProductContentView.as_view(), name="update_product_content_view"),
]
