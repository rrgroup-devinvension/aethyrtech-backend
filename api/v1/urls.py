from django.urls import path, include

urlpatterns = [
    path('core/', include('core.api.v1.urls')),
    path('experience-cloud/', include('experience_cloud.api.v1.urls')),
    path('identity-cloud/', include('identity_cloud.api.v1.urls')),
    path('media-cloud/', include('media_cloud.api.v1.urls')),
]
