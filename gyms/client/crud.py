from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from finance.models import Wallet
from ..models import *
from ..serializers import *
from rest_framework import status, permissions ,generics
from finance.models import Wallet
from rest_framework.pagination import PageNumberPagination
from accounts.models import User
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action




class DefaultPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50



@extend_schema(tags=['Gym'])
class GymListCreateView(generics.ListCreateAPIView):
    queryset = Gym.objects.all().order_by('-average_rating')
    serializer_class = GymSerializer
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    @extend_schema(
        summary="ایجاد باشگاه جدید",
        description="ادمین می‌تواند باشگاه جدیدی ایجاد کند. فیلد owner می‌تواند عدد (id) یا شماره موبایل ۱۲ رقمی باشد.",
        request=GymSerializer,
        responses=GymSerializer,

    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        owner_value = self.request.data.get('owner')
        if not owner_value:
            raise ValueError("owner field is required to assign an owner.")

        # اگر طولش 12 بود یعنی شمارشه، بر اساس phone پیدا کن
        if isinstance(owner_value, str) and len(owner_value) == 11:
            try:
                owner = User.objects.get(phone=owner_value)
            except User.DoesNotExist:
                raise ValueError(f"No user found with phone number: {owner_value}")
        else:
            try:
                owner = User.objects.get(id=owner_value)
            except User.DoesNotExist:
                raise ValueError(f"No user found with id: {owner_value}")

        gym = serializer.save(owner=owner)

        if owner.role != 'owner':
            owner.role = 'owner'
            owner.save(update_fields=['role'])

        Wallet.objects.get_or_create(owner=owner)

        return gym



@extend_schema(tags=['Gym'])
class GymDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Gym.objects.all()
    serializer_class = GymSerializer

    def get_permissions(self):
        if self.request.method in ['DELETE', 'PUT', 'PATCH']:
            # فقط ادمین می‌تونه حذف یا ویرایش کنه
            return [permissions.IsAdminUser()]
        # برای مشاهده جزئیات نیازی به لاگین نیست
        return [permissions.AllowAny()]




@extend_schema(tags=['Gym_images'])
class GymImageViewSet(ViewSet):
    parser_classes = [MultiPartParser, FormParser]

    @action(detail=False, methods=["get"], url_path="gym/(?P<gym_id>\d+)/images")
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
                alt_text=data.get("alt_text", "")
            )
            uploaded_images.append(obj)

        return Response(
            GymImageSerializer(uploaded_images, many=True, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["delete"], url_path="delete")
    def delete_image(self, request, pk=None):
        image = get_object_or_404(GymImage, id=pk)``
        # اختیاری: بررسی دسترسی
        # if image.gym.owner != request.user:
        #     return Response({"error": "شما اجازه حذف این تصویر را ندارید."}, status=status.HTTP_403_FORBIDDEN)
        
        image.delete()
        return Response({"message": "تصویر با موفقیت حذف شد."}, status=status.HTTP_204_NO_CONTENT)