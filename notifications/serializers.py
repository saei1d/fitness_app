from rest_framework import serializers
from django.shortcuts import get_object_or_404

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Read serializer for listing and detail."""

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at', 'data']
        read_only_fields = ['id', 'notification_type', 'title', 'message', 'is_read', 'created_at', 'data']


class AdminSendNotificationSerializer(serializers.Serializer):
    """Write serializer for POST /admin/send/."""

    recipient_id    = serializers.IntegerField(required=False, allow_null=True)
    recipient_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True)
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
