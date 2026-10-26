import re

from rest_framework import serializers
from .models import User, OTP
from .validators import convert_persian_to_english_digits
from datetime import datetime
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field, OpenApiTypes


class PhoneNumberField(serializers.CharField):
    """
    Custom field that converts Persian digits to English digits
    """
    def to_internal_value(self, data):
        # Convert Persian digits to English digits
        data = convert_persian_to_english_digits(data)
        return super().to_internal_value(data)


class CardNumberField(serializers.CharField):
    """
    Bank card number field: accepts Persian/Arabic digits with optional
    spaces/dashes, normalizes them to English digits and validates 16-20 digits.
    """
    default_error_messages = {
        'invalid': 'شماره کارت باید فقط شامل عدد و بین ۱۶ تا ۲۰ رقم باشد.',
        'blank': 'شماره کارت نمی‌تواند خالی باشد.',
        'null': 'شماره کارت نمی‌تواند خالی باشد.',
        'max_length': 'شماره کارت نمی‌تواند بیشتر از ۲۰ رقم باشد.',
    }

    def __init__(self, **kwargs):
        kwargs.setdefault('max_length', 20)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if isinstance(data, str):
            data = convert_persian_to_english_digits(data)
            data = re.sub(r'[\s-]', '', data)
        value = super().to_internal_value(data)
        if not re.fullmatch(r'[0-9]{16,20}', value):
            self.fail('invalid')
        return value


class RequestOTPSerializer(serializers.Serializer):
    phone = PhoneNumberField()


class VerifyOTPSerializer(serializers.Serializer):
    phone = PhoneNumberField()
    code = serializers.CharField()

class EditProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField(read_only=True)
    card_number = CardNumberField(required=False)

    class Meta:
        model = User
        fields = ['full_name', 'birthdate', 'avatar', 'avatar_url', 'card_number']
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


class PublicOwnerSerializer(serializers.ModelSerializer):
    """مشخصات عمومی مالک باشگاه. شماره، تاریخ تولد و پرچم‌های دسترسی اینجا نمی‌آیند."""

    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'full_name', 'avatar_url']

    @extend_schema_field(OpenApiTypes.URI)
    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url


class UserDetailSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField(read_only=True)
    trainer_id = serializers.SerializerMethodField(read_only=True)

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
            'trainer_id',
            'card_number',
        ]

    @extend_schema_field(OpenApiTypes.URI)
    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url

    def get_trainer_id(self, obj):
        if hasattr(obj, 'trainer_profile') and obj.trainer_profile:
            return obj.trainer_profile.id
        return None


class ProfilePhotoUploadSerializer(serializers.Serializer):
    avatar = serializers.ImageField(required=True)


class ProfilePhotoResponseSerializer(serializers.Serializer):
    avatar_url = serializers.URLField(allow_null=True, required=False)


class CheckAuthResponseSerializer(serializers.Serializer):
    is_authenticated = serializers.BooleanField()
    detail = serializers.CharField(required=False)
    user = serializers.JSONField(required=False)


class MakeUserStaffRequestSerializer(serializers.Serializer):
    phone = PhoneNumberField()
    is_staff = serializers.BooleanField(required=False, default=True)


class MakeUserStaffResponseSerializer(serializers.Serializer):
    phone = serializers.CharField()
    is_staff = serializers.BooleanField()


class EnterReferralCodeSerializer(serializers.Serializer):
    referral_code = serializers.CharField(max_length=20)
