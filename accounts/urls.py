from django.urls import path , include

urlpatterns = [
    path('auth/', include('accounts.client.urls')),
    path('admin/', include('accounts.admin.urls')),
]