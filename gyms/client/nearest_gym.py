from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ..models import Gym
from ..serializers import GymSerializer
from django.db.models import ExpressionWrapper, FloatField
from django.db.models.functions import ACos, Cos, Radians, Sin


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
            user_lat = float(request.data.get('latitude'))
            user_lon = float(request.data.get('longitude'))

            # محاسبه فاصله با استفاده از فرمول Haversine در SQL
            # فرمول: 6371 * ACOS(COS(RADIANS(lat1)) * COS(RADIANS(lat2)) * COS(RADIANS(lon2) - RADIANS(lon1)) + SIN(RADIANS(lat1)) * SIN(RADIANS(lat2)))
            nearest_gyms = Gym.objects.annotate(
                distance=ExpressionWrapper(
                    6371 * ACos(
                        Cos(Radians(user_lat)) * Cos(Radians('latitude')) * 
                        Cos(Radians('longitude') - Radians(user_lon)) + 
                        Sin(Radians(user_lat)) * Sin(Radians('latitude'))
                    ),
                    output_field=FloatField()
                )
            ).filter(latitude__isnull=False, longitude__isnull=False).order_by('distance')[:5]

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
