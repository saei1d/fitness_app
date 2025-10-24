from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from ..models import Gym, Package, GroupPackage
from ..serializers import *
from rest_framework import status, permissions


@extend_schema(tags=['Group Package'])
class GroupPackageListCreateView(generics.ListCreateAPIView):
    queryset = GroupPackage.objects.all()
    serializer_class = GroupPackageSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


@extend_schema(tags=['Group Package'])
class GroupPackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GroupPackage.objects.all()
    serializer_class = GroupPackageSerializer
    
    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]



@extend_schema(tags=['Package'])
class PackageListCreateView(generics.ListCreateAPIView):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]


@extend_schema(tags=['Package'])
class PackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]