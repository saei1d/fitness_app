from django.urls import path, include

urlpatterns = [
    path('', include('discount.client.urls')),
]