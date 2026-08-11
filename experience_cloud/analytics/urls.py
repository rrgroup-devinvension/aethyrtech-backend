"""URL routing configuration for the Experience Cloud Analytics application."""

from django.urls import path

from .views import (
    BrandAuditDataView,
    CatalogDetailView,
    CategoryDataView,
    ContentInsightsDataView,
    CROBarriersDataView,
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
    AnalyticsDownloadViewSet,
)
from .action_dashboard_views import (
    ActionPlansView,
    ActionPlansNotifyView,
    MetricSnapshotsView,
    MetricSnapshotsCompareView,
)

app_name = "analytics"

from rest_framework.routers import SimpleRouter
router = SimpleRouter()
router.register(r'', AnalyticsDownloadViewSet, basename='analytics-downloads')

urlpatterns = [
    # Top-Level Overviews
    path("region-dashboard/<int:region_id>/", RegionDashboardDataView.as_view(), name="dashboard-data"),
    path("dashboard-positive/<int:region_id>/", DashboardPositiveDataView.as_view(), name="dashboard-positive"),
    path("insights/<int:region_id>/", InsightsDataView.as_view(), name="insights-data"),
    
    # Action Dashboard
    path("action-plans/<int:region_id>/", ActionPlansView.as_view(), name="action-plans"),
    path("action-plans/<int:region_id>/notify/", ActionPlansNotifyView.as_view(), name="action-plans-notify"),
    path("action-plans/<int:region_id>/<str:task_id>/", ActionPlansView.as_view(), name="action-plans-task"),
    path("metric-snapshots/<int:region_id>/", MetricSnapshotsView.as_view(), name="metric-snapshots"),
    path("metric-snapshots/<int:region_id>/compare/", MetricSnapshotsCompareView.as_view(), name="metric-snapshots-compare"),

    # Region-specific JSON data APIs
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

    path("generate-content/", GenerateContentView.as_view(), name="generate_content_view"),
    path("update-product-content/", UpdateProductContentView.as_view(), name="update_product_content_view"),
] + router.urls
