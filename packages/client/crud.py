from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from ..models import Gym
from ..serializers import *
from rest_framework import status, permissions


@extend_schema(tags=['package'])
class PackageListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    queryset = Package.objects.all()
    serializer_class = PackageSerializer


@extend_schema(tags=['package'])
class PackageDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
