from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Ticket, TicketMessage


class TicketSerializer(serializers.ModelSerializer):
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    admin = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), allow_null=True, required=False)
    message = serializers.CharField(write_only=True, help_text="متن اولیه تیکت")

    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'message', 'creator', 'admin', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        message_text = validated_data.pop('message', '')  # Extract message from validated_data
        
        if request and request.user and request.user.is_authenticated:
            validated_data['creator'] = request.user
        
        # Create the ticket first
        ticket = super().create(validated_data)
        
        # Create the initial message if message text is provided
        if message_text:
            TicketMessage.objects.create(
                ticket=ticket,
                author=request.user,
                message=message_text
            )
        
        return ticket


class TicketMessageSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    author_name = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = TicketMessage
        fields = ['id', 'ticket', 'author', 'author_name', 'message', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']

    def validate(self, attrs):
        request = self.context.get('request')
        ticket = attrs.get('ticket')
        if request and request.user and ticket:
            user = request.user
            # Only ticket creator or staff can post messages
            if not (user.is_staff or ticket.creator_id == user.id):
                raise serializers.ValidationError('اجازه ارسال پیام برای این تیکت را ندارید.')
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['author'] = request.user
        return super().create(validated_data)


class TicketDetailSerializer(serializers.ModelSerializer):
    creator = serializers.PrimaryKeyRelatedField(read_only=True)
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    admin = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all(), allow_null=True, required=False)
    admin_name = serializers.CharField(source='admin.username', read_only=True)
    messages = TicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'subject', 'creator', 'creator_name', 'admin', 'admin_name', 'status', 'created_at', 'updated_at', 'messages']
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']


    

