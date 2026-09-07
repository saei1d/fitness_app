from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from ..models import Gym
from ..serializers import GymSerializer
from .crud import DefaultPagination
from django.db.models import ExpressionWrapper, FloatField
from django.db.models.functions import ACos, Cos, Radians, Sin


@extend_schema(tags=['nearest_gym'])
class NearestGymsView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = GymSerializer
    pagination_class = DefaultPagination

    @extend_schema(
        parameters=[
            {
                'name': 'latitude',
                'type': float,
                'required': True,
                'description': 'مختصات عرض جغرافیایی کاربر',
            },
            {
                'name': 'longitude',
                'type': float,
                'required': True,
                'description': 'مختصات طول جغرافیایی کاربر',
            },
        ],
        responses={200: GymSerializer(many=True)},
        description="باشگاه‌های نزدیک را با فاصله‌ی مرتب شده برمی‌گرداند. از پارامترهای latitude و longitude در کوئری استرینگ استفاده کنید."
    )
    def get(self, request, *args, **kwargs):
        try:
            # دریافت مختصات کاربر از کوئری پارامترها
            user_lat = float(request.query_params.get('latitude'))
            user_lon = float(request.query_params.get('longitude'))

            # محاسبه فاصله با استفاده از فرمول Haversine در SQL
            # فرمول: 6371 * ACOS(COS(RADIANS(lat1)) * COS(RADIANS(lat2)) * COS(RADIANS(lon2) - RADIANS(lon1)) + SIN(RADIANS(lat1)) * SIN(RADIANS(lat2)))
            queryset = Gym.objects.annotate(
                distance=ExpressionWrapper(
                    6371 * ACos(
                        Cos(Radians(user_lat)) * Cos(Radians('latitude')) * 
                        Cos(Radians('longitude') - Radians(user_lon)) + 
                        Sin(Radians(user_lat)) * Sin(Radians('latitude'))
                    ),
                    output_field=FloatField()
                )
            ).filter(latitude__isnull=False, longitude__isnull=False).order_by('distance')

            # اعمال pagination
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            # اگر pagination غیرفعال باشد
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

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
