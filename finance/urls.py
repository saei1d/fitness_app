from django.urls import include, path

urlpatterns = [
    path('', include('finance.client.urls')),
    path('admin/finance/', include('finance.backoffice.urls')),
    path('finance/', include('finance.client.urls')),  # legacy alias
    path('finance/admin/', include('finance.backoffice.urls')),  # legacy alias
]
