from django.urls import path, include

urlpatterns = [
    path('ticket/', include('ticket.client.urls')),
]

