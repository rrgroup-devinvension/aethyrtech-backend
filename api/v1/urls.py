from django.urls import path, include
from .routers import urlpatterns as router_urls
from apps.users.views import ProfileView, ChangePasswordView

urlpatterns = [
    path("", include(router_urls)),
    path("analysis/", include("apps.analysis.urls")),
    path("auth/", include("apps.auths.urls")),

    # Explicit user profile endpoints under /api/v1/users/
    path("users/", include("apps.users.urls")),
    path("scheduler/", include("apps.tasks.urls")),

    # path("users/profile/", ProfileView.as_view(), name="profile"),
    # path("users/profile/change-password/", ChangePasswordView.as_view(), name="profile-change-password"),
]
