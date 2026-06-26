from django.urls import include, path

urlpatterns = [
    path('', include('ticket.client.urls')),
]
