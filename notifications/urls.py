from django.urls import include, path

urlpatterns = [
    path('', include('notifications.client.urls')),
]
