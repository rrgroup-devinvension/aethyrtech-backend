from django.urls import path, include
from .routers import urlpatterns as router_urls
from apps.users.views import ProfileView, ChangePasswordView

urlpatterns = [
    path("", include(router_urls)),
    path("analysis/", include("apps.analysis.urls")),
    path("auth/", include("apps.auths.urls")),
    path("users/", include("apps.users.urls")),
    path("scheduler/", include("apps.tasks.urls")),
    path("", include("apps.category.urls")),
    path("", include("apps.brand.urls")),
]
