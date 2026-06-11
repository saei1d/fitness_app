from django.urls import include, path

urlpatterns = [
    path('auth/', include('accounts.client.urls')),
    path('admin/accounts/', include('accounts.backoffice.urls')),
    path('admin/', include('accounts.backoffice.urls')),  # legacy alias
]
