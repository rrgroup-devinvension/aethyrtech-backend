from django.urls import include, path

urlpatterns = [
    path('auth/', include('core.authentication.urls')),
    path('analytics/', include('core.analytics.urls')),
    path('llm/', include('core.llm_providers.urls')),
    path('users/', include('core.users.urls')),
    path('categories/', include('core.categories.urls')),
    path('team-management/', include('core.team_management.urls')),
    path('', include('core.organizations.urls')),
]
