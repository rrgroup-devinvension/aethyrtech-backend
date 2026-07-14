from django.urls import path, include

urlpatterns = [
    path('auth/', include('core.authentication.urls')),
    path('analytics/', include('core.analytics.urls')),
    path('llm/', include('core.llm_providers.urls')),
    path('users/', include('core.users.urls')),
    path('categories/', include('core.categories.urls')),
    path('organizations/', include('core.organizations.urls')),
]
