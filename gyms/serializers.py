from rest_framework import serializers
from .models import GymImage, Gym
from django.contrib.gis.geos import Point
from .models import Gym


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
    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)

    class Meta:
        model = Gym
        fields = ["id", "owner", "name", "description", "address", "working_hours",
                  "banner", "latitude", "longitude"]

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
