from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import generics, permissions, status, serializers
from rest_framework.response import Response
from finance.models import Wallet
from ..models import GymImage
from ..serializers import GymImageSerializer
from ..models import Gym
from ..serializers import *
from rest_framework import status, permissions
from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema
from ..models import Gym
from finance.models import Wallet
from ..serializers import GymSerializer
from rest_framework.pagination import PageNumberPagination
from accounts.models import User

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

    def perform_create(self, serializer):
        # فقط ادمین اینجا میاد
        owner_id = self.request.data.get('owner')
        if not owner_id:
            raise ValueError("owner field is required to assign an owner.")

        try:
            owner = User.objects.get(id=owner_id)
        except User.DoesNotExist:
            raise ValueError(f"No user found with phone number: {phone}")

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





@extend_schema(
    tags=["GymImage"],
    request=GymImageBulkUploadRequestSerializer,
    responses=GymImageSerializer(many=True),
)
class GymImageBulkUploadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = GymImageBulkUploadRequestSerializer  # 👈 اضافه شد

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        gym_id = serializer.validated_data["gym"]
        images = serializer.validated_data["images"]
        alt_texts = serializer.validated_data.get("alt_texts", [])

        if len(alt_texts) < len(images):
            alt_texts += [""] * (len(images) - len(alt_texts))

        gym_images = []
        for image, alt_text in zip(images, alt_texts):
            gym_image = GymImage.objects.create(
                gym_id=gym_id,
                image=image,
                alt_text=alt_text
            )
            gym_images.append(gym_image)

        return Response(
            GymImageSerializer(gym_images, many=True).data,
            status=status.HTTP_201_CREATED
        )
