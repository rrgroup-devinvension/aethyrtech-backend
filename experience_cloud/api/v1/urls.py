from django.urls import path, include

urlpatterns = [
    path('analytics/', include('experience_cloud.analytics.urls')),
    path('api-provider/', include('experience_cloud.api_provider.urls')),
    path('catalog/', include('experience_cloud.catalog.urls')),
    path('executions/', include('experience_cloud.executions.urls')),
    path('json-generator/', include('experience_cloud.json_generator.urls')),
    path('market-data/', include('experience_cloud.market_data.urls')),
]
