import json

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from ..models import Gym
from ..serializers import GymSerializer


@extend_schema(tags=['nearest_gym'])
class NearestGymsView(APIView):
    @extend_schema(
        request=GymSerializer,
        responses={200: dict},
        description="فقط lat , lon کاربر را ارسال کنید"
    )
    def post(self, request, *args, **kwargs):
        try:
            # Get data from request (DRF automatically parses JSON)
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))

            # Create a Point object for the user's location
            user_location = Point(longitude, latitude, srid=4326)

            # Query the 5 nearest gyms using PostGIS Distance function
            nearest_gyms = Gym.objects.annotate(
                distance=Distance('location', user_location)
            ).order_by('distance')[:5]

            # Prepare response data
            gyms_data = [
                {
                    'id': gym.id,
                    'name': gym.name,
                    'latitude': gym.latitude,
                    'longitude': gym.longitude,
                    'address': gym.address,
                    'distance_meters': gym.distance.m,  # Distance in meters
                    'banner_url': gym.banner.url if gym.banner else None,
                }
                for gym in nearest_gyms
            ]

            return Response({'gyms': gyms_data}, status=status.HTTP_200_OK)

        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid input data'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
