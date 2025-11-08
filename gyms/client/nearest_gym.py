from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from ..models import Gym
from ..serializers import GymSerializer


@extend_schema(tags=['nearest_gym'])
class NearestGymsView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=GymSerializer,
        responses={200: GymSerializer(many=True)},
        description="فقط lat , lon کاربر را ارسال کنید"
    )
    def post(self, request, *args, **kwargs):
        try:
            # دریافت مختصات کاربر از بدنه درخواست
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))

            # ساخت نقطه جغرافیایی برای موقعیت کاربر
            user_location = Point(longitude, latitude, srid=4326)

            # پیدا کردن نزدیک‌ترین باشگاه‌ها
            nearest_gyms = Gym.objects.annotate(
                distance=Distance('location', user_location)
            ).order_by('distance')[:5]

            # سریالایز کردن باشگاه‌ها (فاصله درون Serializer محاسبه می‌شود)
            serializer = GymSerializer(nearest_gyms, many=True, context={'request': request})

            return Response({'gyms': serializer.data}, status=status.HTTP_200_OK)

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
