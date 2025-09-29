from django.urls import path
from .CRUD import GymGeoListCreateView, GymGeoDetailView

urlpatterns = [
    path("gyms/", GymGeoListCreateView.as_view(), name="gym-list-create"),
    path("gyms/<int:pk>/", GymGeoDetailView.as_view(), name="gym-detail"),
]
