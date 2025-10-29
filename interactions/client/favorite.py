from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework import serializers
from drf_spectacular.utils import extend_schema
from ..models import Favorite
from ..serializers import FavoriteSerializer


@extend_schema(tags=['Favorite'])
class FavoriteListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: FavoriteSerializer(many=True)},
        summary='لیست علاقه‌مندی‌ها',
        description='نمایش لیست باشگاه‌های مورد علاقه کاربر'
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        request=FavoriteSerializer,
        responses={201: FavoriteSerializer, 400: dict},
        summary='افزودن به علاقه‌مندی‌ها',
        description='افزودن باشگاه به لیست علاقه‌مندی‌ها'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        gym = self.request.data.get('gym')
        if Favorite.objects.filter(user=self.request.user, gym_id=gym).exists():
            raise serializers.ValidationError({'detail': 'This gym is already in favorites.'})
        serializer.save(user=self.request.user)


@extend_schema(tags=['Favorite'])
class FavoriteDetailView(generics.DestroyAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={204: None, 404: dict},
        summary='حذف از علاقه‌مندی‌ها',
        description='حذف باشگاه از لیست علاقه‌مندی‌ها'
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)