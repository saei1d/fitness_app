from django.urls import include, path

urlpatterns = [
    path('', include('gyms.client.urls')),
    path('gym/', include('gyms.client.urls')),  # legacy alias
]
