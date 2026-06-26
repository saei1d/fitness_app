from rest_framework import serializers
from .models import User, OTP
from datetime import datetime
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field, OpenApiTypes


class RequestOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    code = serializers.CharField()

class EditProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['full_name', 'birthdate', 'avatar', 'avatar_url']
        extra_kwargs = {
            'avatar': {'required': False, 'allow_null': True, 'write_only': True},
        }

    @extend_schema_field(OpenApiTypes.URI)
    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    def update(self, instance, validated_data):
        new_avatar = validated_data.get('avatar')
        if new_avatar and instance.avatar:
            instance.avatar.delete(save=False)
        return super().update(instance, validated_data)


class UserDetailSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'phone',
            'full_name',
            'birthdate',
            'role',
            'is_phone_verified',
            'is_staff',
            'is_superuser',
            'referral_code',
            'referred_by',
            'is_active',
            'date_joined',
            'avatar_url',
        ]

    @extend_schema_field(OpenApiTypes.URI)
    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url


class ProfilePhotoUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(required=True)


class ProfilePhotoResponseSerializer(serializers.Serializer):
    avatar_url = serializers.URLField(allow_null=True, required=False)


class CheckAuthResponseSerializer(serializers.Serializer):
    is_authenticated = serializers.BooleanField()
    detail = serializers.CharField(required=False)
    user = serializers.JSONField(required=False)


class EnterReferralCodeSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=20)
