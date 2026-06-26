from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.urls import re_path
from django.views.static import serve as static_serve
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

api_v1_patterns = [
    path('', include('accounts.urls')),
    path('', include('gyms.urls')),
    path('', include('packages.urls')),
    path('', include('finance.urls')),
    path('', include('interactions.urls')),
    path('', include('ticket.urls')),
    path('', include('discount.urls')),
    path('', include('notifications.urls')),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'docs/',
        SpectacularSwaggerView.as_view(url_name='api-v1:schema'),
        name='swagger-ui'
    ),
    path(
        'redoc/',
        SpectacularRedocView.as_view(url_name='api-v1:schema'),
        name='redoc'
    ),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include((api_v1_patterns, 'api-v1'))),
]

# Django's static() helper is a no-op when DEBUG=False, so add an explicit
# media route for environments without a separate web server.
urlpatterns += [
    re_path(
        r'^media/(?P<path>.*)$',
        static_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
