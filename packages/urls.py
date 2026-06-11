from django.urls import include, path

urlpatterns = [
    path('', include('packages.client.urls')),
    path('package/', include('packages.client.urls')),  # legacy alias
]
