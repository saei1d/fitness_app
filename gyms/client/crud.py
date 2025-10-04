from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.response import Response

from ..models import Gym
from ..serializers import *
from rest_framework import status, permissions


@extend_schema(tags=['Gym'])
class GymListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    queryset = Gym.objects.all()
    serializer_class = GymSerializer


@extend_schema(tags=['Gym'])
class GymDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Gym.objects.all()
    serializer_class = GymSerializer

from rest_framework import generics, permissions, status, serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from ..models import GymImage
from ..serializers import GymImageSerializer


class GymImageBulkUploadRequestSerializer(serializers.Serializer):
    gym = serializers.IntegerField(required=True)
    images = serializers.ListField(
        child=serializers.ImageField(), required=True
    )
    alt_texts = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False
    )


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
