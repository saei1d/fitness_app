from rest_framework import serializers
from .models import GymGeo, GymImage


class GymImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GymImage
        fields = ["image", "alt_text", "order", "uploaded_at"]


class GymGeoSerializer(serializers.ModelSerializer):
    images = GymImageSerializer(many=True, read_only=True)

    class Meta:
        model = GymGeo
        fields = [
            "owner", "name", "description", "location", "address",
            "working_hours", "banner", "created_at", "updated_at", "images"
        ]
