from django.urls import path
from .crud import *
from .nearest_gym import *

urlpatterns = [
    path("gyms/", GymListCreateView.as_view(), name="gym-list-create"),
    path("gyms/<int:pk>/", GymDetailView.as_view(), name="gym-detail"),
    path("images/upload/", GymImageUploadView.as_view(), name="gymimage-upload"),
    path('nearest-gyms/', NearestGymsView.as_view(), name='nearest_gyms'),

]
