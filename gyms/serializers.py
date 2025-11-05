from rest_framework import serializers
from .models import GymImage, Gym
from django.contrib.gis.geos import Point
from .models import Gym
from accounts.serializers import UserDetailSerializer



class GymImageFlexibleSerializer(serializers.Serializer):
    """
    Serializer که هم فایل تکی بگیره، هم چندتایی.
    """
    gym = serializers.IntegerField(required=True)
    images = serializers.ListField(
        child=serializers.ImageField(), required=False
    )
    image = serializers.ImageField(required=False)
    alt_texts = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False
    )
    alt_text = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # باید یا image یا images وجود داشته باشه
        if not attrs.get("image") and not attrs.get("images"):
            raise serializers.ValidationError("حداقل یک تصویر لازم است.")
        return attrs



class GymSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    owner = serializers.CharField(write_only=True)
    owner_data = UserDetailSerializer(source='owner', read_only=True)
    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)

    class Meta:
        model = Gym
        fields = [
            "id", "owner", "owner_data", "name", "description", "address",
            "working_hours", "banner", "latitude", "longitude",
            "comments", "average_rating", "price"
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if instance.banner and hasattr(instance.banner, 'url'):
            rep['banner'] = request.build_absolute_uri(instance.banner.url) if request else instance.banner.url
        else:
            rep['banner'] = None
        return rep


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
