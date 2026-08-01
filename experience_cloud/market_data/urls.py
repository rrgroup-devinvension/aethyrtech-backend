from django.urls import path

from .views import (
    HierarchyCategoryListView,
    HierarchyKeywordListView,
    HierarchyLocationListView,
    HierarchyPlatformListView,
    MarketDataStatsView,
    ProductsDetailView,
    ProductsListView,
    RunDataDumpView,
    StopDataDumpView,
    DebugRunDataDumpView,
)

urlpatterns = [
    path('categories/', HierarchyCategoryListView.as_view(), name='hierarchy-categories'),
    path('platforms/', HierarchyPlatformListView.as_view(), name='hierarchy-platforms'),
    path('keywords/', HierarchyKeywordListView.as_view(), name='hierarchy-keywords'),
    path('locations/', HierarchyLocationListView.as_view(), name='hierarchy-locations'),
    path('run/', RunDataDumpView.as_view(), name='run-data-dump'),
    path('products/', ProductsListView.as_view(), name='products-list'),
    path('products/<uuid:id>/', ProductsDetailView.as_view(), name='products-detail'),
    path('stats/', MarketDataStatsView.as_view(), name='market-data-stats'),
    path('locations/<int:id>/stop/', StopDataDumpView.as_view(), name='stop-data-dump'),
    path('debug-run/', DebugRunDataDumpView.as_view(), name='debug-data-dump'),
]
