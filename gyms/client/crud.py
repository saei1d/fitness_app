from django.shortcuts import get_object_or_404
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from gyms.services import promote_gym_owner, resolve_gym_owner

from ..models import Gym, GymImage
from ..serializers import GymImageFlexibleSerializer, GymImageSerializer, GymSerializer


class IsAdminOrGymOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if getattr(view, "action", None) == "list_images":
            return True
        return request.user and request.user.is_authenticated

    def has_gym_permission(self, request, gym):
        return request.user.is_staff or gym.owner_id == request.user.id


class DefaultPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


@extend_schema(tags=["Gym"])
class GymListCreateView(generics.ListCreateAPIView):
    queryset = Gym.objects.all().order_by("-average_rating")
    serializer_class = GymSerializer
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by gender based on packages
        gender = self.request.query_params.get('gender')
        if gender:
            queryset = queryset.filter(packages__gender=gender).distinct()
        
        # Filter by price range based on packages
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(packages__price__gte=min_price).distinct()
        if max_price:
            queryset = queryset.filter(packages__price__lte=max_price).distinct()
        
        return queryset

    @extend_schema(
        summary="لیست باشگاه‌ها",
        description=(
            "لیست تمام باشگاه‌ها را برمی‌گرداند. بدون احراز هویت قابل دسترسی است. "
            "فیلترها بر اساس پکیج‌های هر باشگاه اعمال می‌شوند:\n"
            "- gender: فیلتر بر اساس جنسیت پکیج (male/female)\n"
            "- min_price: حداقل قیمت پکیج\n"
            "- max_price: حداکثر قیمت پکیج"
        ),
        parameters=[
            {
                'name': 'gender',
                'type': str,
                'required': False,
                'description': 'فیلتر جنسیت پکیج (male/female)',
            },
            {
                'name': 'min_price',
                'type': float,
                'required': False,
                'description': 'حداقل قیمت پکیج',
            },
            {
                'name': 'max_price',
                'type': float,
                'required': False,
                'description': 'حداکثر قیمت پکیج',
            },
        ],
        responses=GymSerializer,
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @extend_schema(
        summary="ایجاد باشگاه جدید",
        description=(
            "ادمین می‌تواند باشگاه جدیدی ایجاد کند. فیلد owner می‌تواند "
            "شناسه کاربر یا شماره موبایل باشد."
        ),
        request=GymSerializer,
        responses=GymSerializer,
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        owner_value = self.request.data.get("owner")
        try:
            owner = resolve_gym_owner(owner_value)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        with transaction.atomic():
            gym = serializer.save(owner=owner)
            promote_gym_owner(owner)
            return gym


@extend_schema(tags=["Gym"])
class GymDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Gym.objects.all()
    serializer_class = GymSerializer

    def get_permissions(self):
        if self.request.method in ["DELETE", "PUT", "PATCH"]:
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


@extend_schema(tags=["Gym_images"])
class GymImageViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAdminOrGymOwner]

    @action(detail=False, methods=["get"], url_path=r"gym/(?P<gym_id>\d+)/images")
    def list_images(self, request, gym_id=None):
        gym = get_object_or_404(Gym, id=gym_id)
        images = GymImage.objects.filter(gym=gym)
        serializer = GymImageSerializer(images, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload_image(self, request):
        serializer = GymImageFlexibleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        gym = get_object_or_404(Gym, id=data["gym"])
        permission = IsAdminOrGymOwner()
        if not permission.has_gym_permission(request, gym):
            raise PermissionDenied("You can only upload images for your own gym.")

        uploaded_images = []

        if "images" in data:
            alt_texts = data.get("alt_texts", [""] * len(data["images"]))
            for image, alt_text in zip(data["images"], alt_texts):
                obj = GymImage.objects.create(gym=gym, image=image, alt_text=alt_text)
                uploaded_images.append(obj)
        else:
            obj = GymImage.objects.create(
                gym=gym,
                image=data["image"],
                alt_text=data.get("alt_text", ""),
            )
            uploaded_images.append(obj)

        return Response(
            GymImageSerializer(uploaded_images, many=True, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_image(self, request, pk=None):
        image = get_object_or_404(GymImage.objects.select_related("gym"), id=pk)
        permission = IsAdminOrGymOwner()
        if not permission.has_gym_permission(request, image.gym):
            raise PermissionDenied("You can only delete images for your own gym.")

        image.delete()
        return Response({"message": "تصویر با موفقیت حذف شد."}, status=status.HTTP_204_NO_CONTENT)
