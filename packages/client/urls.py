from django.urls import path

from packages.client.crud import *

urlpatterns = [
    path("packages/", PackageListCreateView.as_view(), name="gym-list-create"),
    path("packages/<int:pk>/", PackageDetailView.as_view(), name="gym-detail"),
]
