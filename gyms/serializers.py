from rest_framework import serializers
from .models import GymImage, Gym
from django.contrib.gis.geos import Point
from .models import Gym
from accounts.serializers import UserDetailSerializer  # اگه چنین سریالایزری داری
from accounts.models import User


class GymImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GymImage
        fields = ["gym", "image", "alt_text", "order", "uploaded_at"]

    def create(self, validated_data):
        gym_id = validated_data["gym"]
        images = validated_data["images"]
        alt_texts = validated_data.get("alt_texts", [""] * len(images))

        gym_images = []
        for image, alt_text in zip(images, alt_texts):
            gym_image = GymImage.objects.create(
                gym_id=gym_id,
                image=image,
                alt_text=alt_text
            )
            gym_images.append(gym_image)
        return gym_images


class GymSerializer(serializers.ModelSerializer):
    # owner به صورت رشته میاد (id یا شماره موبایل)
    owner = serializers.CharField(write_only=True)
    owner_data = UserDetailSerializer(source='owner', read_only=True)

    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)
    
    banner = serializers.SerializerMethodField()

    class Meta:
        model = Gym
        fields = [
            "id", "owner", "owner_data", "name", "description", "address",
            "working_hours", "banner", "latitude", "longitude",
            "comments", "average_rating"
        ]
    
    def get_banner(self, obj):
        print(f"Banner: {obj.banner}")  # دیباگ
        print(f"Has url: {hasattr(obj.banner, 'url') if obj.banner else False}")  # دیباگ
        if obj.banner and hasattr(obj.banner, 'url'):
            request = self.context.get('request')
            print(f"Request: {request}")  # دیباگ
            if request:
                return request.build_absolute_uri(obj.banner.url)
        return None

    def create(self, validated_data):
        latitude = validated_data.pop("latitude")
        longitude = validated_data.pop("longitude")
        validated_data["location"] = Point(float(longitude), float(latitude), srid=4326)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        latitude = validated_data.pop("latitude", None)
        longitude = validated_data.pop("longitude", None)
        if latitude and longitude:
            validated_data["location"] = Point(float(longitude), float(latitude), srid=4326)
        return super().update(instance, validated_data)

class GymImageBulkUploadRequestSerializer(serializers.Serializer):
    gym = serializers.IntegerField(required=True)
    images = serializers.ListField(
        child=serializers.ImageField(), required=True
    )
    alt_texts = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False
    )