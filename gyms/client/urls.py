from django.urls import path, include
from .crud import *
from .nearest_gym import *
from rest_framework.routers import DefaultRouter

urlpatterns = [
    path("gyms/", GymListCreateView.as_view(), name="gym-list-create"),
    path("gyms/<int:pk>/", GymDetailView.as_view(), name="gym-detail"),
    path("nearest-gyms/", NearestGymsView.as_view(), name="nearest_gyms"),
]

router = DefaultRouter()
router.register(r"gym-images", GymImageViewSet, basename="gym-image")

urlpatterns += router.urls
