from django.urls import path, include

urlpatterns = [
    path('purchase/', include('finance.client.urls')),
]
