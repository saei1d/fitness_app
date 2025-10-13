from django.urls import path

from packages.client.crud import *

urlpatterns = [
    path("group-packages/", GroupPackageListCreateView.as_view(), name="group-package-list-create"),
    path("group-packages/<int:pk>/", GroupPackageDetailView.as_view(), name="group-package-detail"),
    path("packages/", PackageListCreateView.as_view(), name="package-list-create"),
    path("packages/<int:pk>/", PackageDetailView.as_view(), name="package-detail"),
]
