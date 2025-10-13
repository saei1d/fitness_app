from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from ..models import Gym, Package, GroupPackage
from ..serializers import *
from rest_framework import status, permissions


@extend_schema(tags=['Group Package'])
class GroupPackageListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = GroupPackage.objects.all()
    serializer_class = GroupPackageSerializer


@extend_schema(tags=['Group Package'])
class GroupPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = GroupPackage.objects.all()
    serializer_class = GroupPackageSerializer


@extend_schema(tags=['Package'])
class PackageListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Package.objects.all()
    serializer_class = PackageSerializer


@extend_schema(tags=['Package'])
class PackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
