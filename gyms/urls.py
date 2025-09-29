from django.urls import path , include

urlpatterns = [
    path('gym/',include('gyms.client.urls')),
]