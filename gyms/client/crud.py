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


@extend_schema(tags=["GymImage"])
class GymImageBulkUploadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        gym_id = request.data.get("gym")
        images = request.FILES.getlist("images")
        alt_texts = request.data.getlist("alt_texts") if "alt_texts" in request.data else []

        if not gym_id or not images:
            return Response(
                {"detail": "gym و حداقل یک image الزامی است."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(alt_texts) < len(images):
            # پر کردن alt_texts خالی برای عکس‌های اضافه
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

