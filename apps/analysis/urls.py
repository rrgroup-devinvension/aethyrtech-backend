from django.urls import path
from django.urls import path
from .views import (
    DashboardDataView,
    BrandDashboardDataView,
    IncentiveInsightsDataView,
    InsightsDataView,
    DashboardPositiveDataView,
    PdpInsightsDataView,
    CROBarriersDataView,
    CategoryDataView,
    BrandAuditDataView,
    PlpInsightsDataView,
    ProductCatalogDataView,
    CatalogDetailView,
    ReportsDataView,
    ContentInsightsDataView,
    GenerateContentView,
    ReviewsInsightsDataView,
    UpdateProductContentView,
    contact_api
)

urlpatterns = [
    path("dashboard/", DashboardDataView.as_view(), name="dashboard_data_view"),
    path("brand-dashboard/<int:brand_id>/", BrandDashboardDataView.as_view(), name="brand_dashboard_data_view"),
    path("insights/<int:brand_id>/", InsightsDataView.as_view(), name="insights_data_view"),
    path("dashboard-positive/<int:brand_id>/", DashboardPositiveDataView.as_view(), name="dashboard_positive_data_view"),
    path("cro-barriers/<int:brand_id>/", CROBarriersDataView.as_view(), name="cro_barriers_data_view"),
    path("incentive-insights/<int:brand_id>/", IncentiveInsightsDataView.as_view(), name="incentive_insights_data_view"),
    path("plp-insights/<int:brand_id>/", PlpInsightsDataView.as_view(), name="plp_insights_data_view"),
    path("pdp-insights/<int:brand_id>/", PdpInsightsDataView.as_view(), name="plp_insights_data_view"),
    path("reviews-insights/<int:brand_id>/", ReviewsInsightsDataView.as_view(), name="reviews_insights_data_view"),
    path("category/<int:brand_id>/", CategoryDataView.as_view(), name="category_view_data_view"),
    path("brand-audit/<int:brand_id>/", BrandAuditDataView.as_view(), name="brand_audit_data_view"),
    path("product-catalog/<int:brand_id>/", ProductCatalogDataView.as_view(), name="product_catalog_data_view"),
    path("catalog-detail/<int:brand_id>/<str:product_id>/", CatalogDetailView.as_view(), name="catalog_detail_view"),
    path("reports/<int:brand_id>/", ReportsDataView.as_view(), name="reports_data_view"),
    path("content-insights/<int:brand_id>/", ContentInsightsDataView.as_view(), name="content_insights_data_view"),
    path("generate-content/", GenerateContentView.as_view()),
    path("update-product-content/", UpdateProductContentView.as_view()),
    path('contact/', contact_api),
]
