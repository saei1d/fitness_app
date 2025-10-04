from django.urls import path , include

urlpatterns = [
    path('package/', include('packages.client.urls')),
]