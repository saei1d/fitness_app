from rest_framework.routers import DefaultRouter
from .review import ReviewViewSet
from django.urls import path
from .favorite import FavoriteListCreateView, FavoriteDetailView

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')

urlpatterns = router.urls + [
    path('favorites/', FavoriteListCreateView.as_view(), name='favorite-list-create'),
    path('favorites/<int:pk>/', FavoriteDetailView.as_view(), name='favorite-detail'),
]