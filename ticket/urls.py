from django.urls import include, path

urlpatterns = [
    path('', include('ticket.client.urls')),
    path('ticket/', include('ticket.client.urls')),  # legacy alias
]
