from rest_framework import serializers
from django.shortcuts import get_object_or_404
from accounts.validators import convert_persian_to_english_digits

from .models import Notification
from .utils import to_jalali


class NotificationSerializer(serializers.ModelSerializer):
    """Read serializer for listing and detail."""
    created_at_jalali = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at', 'created_at_jalali', 'data']
        read_only_fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at', 'created_at_jalali', 'data']

    def get_created_at_jalali(self, obj):
        return to_jalali(obj.created_at)


class PhoneNumberField(serializers.CharField):
    """
    Custom field that converts Persian digits to English digits
    """
    def to_internal_value(self, data):
        # Convert Persian digits to English digits
        data = convert_persian_to_english_digits(data)
        return super().to_internal_value(data)


class AdminSendNotificationSerializer(serializers.Serializer):
    """Write serializer for POST /admin/send/."""

    recipient_id    = serializers.IntegerField(required=False, allow_null=True)
    recipient_phone = PhoneNumberField(required=False, allow_null=True, allow_blank=True)
    title           = serializers.CharField(max_length=255)
    message         = serializers.CharField(max_length=2000)
    notification_type = serializers.ChoiceField(choices=Notification.NotificationType.choices)

    def validate(self, attrs):
        if not attrs.get('recipient_id') and not attrs.get('recipient_phone'):
            raise serializers.ValidationError(
                {"non_field_errors": "recipient_id or recipient_phone is required"}
            )
        return attrs

    def resolve_recipient(self):
        from accounts.models import User
        rid   = self.validated_data.get('recipient_id')
        phone = self.validated_data.get('recipient_phone')
        if rid:
            return get_object_or_404(User, pk=rid)
        return get_object_or_404(User, phone=phone)
