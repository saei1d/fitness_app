# views.py
from rest_framework import generics
from ..models import GymGeo
from ..serializers import GymGeoSerializer


# لیست همه‌ی باشگاه‌ها + ساختن باشگاه جدید
class GymGeoListCreateView(generics.ListCreateAPIView):
    queryset = GymGeo.objects.all()
    serializer_class = GymGeoSerializer


# جزئیات / آپدیت / حذف یک باشگاه
class GymGeoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = GymGeo.objects.all()
    serializer_class = GymGeoSerializer
