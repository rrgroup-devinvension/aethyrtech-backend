from django.urls import path, include
from .routers import urlpatterns as router_urls

urlpatterns = [
    path("", include(router_urls)),
    path("analysis/", include("apps.analysis.urls")),
    path("auth/", include("apps.auths.urls")),
]
