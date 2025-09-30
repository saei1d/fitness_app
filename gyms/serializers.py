from rest_framework import serializers
from .models import GymImage, Gym


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
    images = GymImageSerializer(many=True, read_only=True)

    class Meta:
        model = Gym
        fields = [
            "owner", "name", "description", "latitude", "longitude", "address",
            "working_hours", "banner", "created_at", "updated_at", "images"
        ]
