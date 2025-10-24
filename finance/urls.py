from django.urls import path, include

urlpatterns = [
    path('finance/', include('finance.client.urls')),
    path('finance/admin/', include('finance.admin.urls')),
]
