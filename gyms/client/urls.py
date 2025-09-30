from django.urls import path
from .crud import *

urlpatterns = [
    path("gyms/", GymListCreateView.as_view(), name="gym-list-create"),
    path("gyms/<int:pk>/", GymDetailView.as_view(), name="gym-detail"),
    path("images/upload/", GymImageBulkUploadView.as_view(), name="gymimage-upload"),

]
