from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Ticket, TicketMessage


class TicketSerializer(serializers.ModelSerializer):
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    admin = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), allow_null=True, required=False)

    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'creator', 'admin', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['creator'] = request.user
        return super().create(validated_data)


class TicketMessageSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'ticket', 'author', 'message', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']

    def validate(self, attrs):
        request = self.context.get('request')
        ticket = attrs.get('ticket')
        if request and request.user and ticket:
            user = request.user
            # Only ticket creator, assigned admin, or staff can post
            if not (user.is_staff or ticket.creator_id == user.id or (ticket.admin_id == user.id if ticket.admin_id else False)):
                raise serializers.ValidationError('اجازه ارسال پیام برای این تیکت را ندارید.')
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['author'] = request.user
        return super().create(validated_data)


    

