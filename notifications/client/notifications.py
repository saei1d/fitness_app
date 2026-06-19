import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.permissions import IsAdminUser, IsNotificationOwner
from notifications.serializers import AdminSendNotificationSerializer, NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationListView(generics.ListAPIView):
    """
    GET /notifications/
    - Admin (role='admin' or is_superuser): returns ALL notifications
    - Owner/Customer: returns only own notifications
    Ordered by -created_at, paginated.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.select_related('recipient')
        if getattr(user, 'role', None) == 'admin' or user.is_superuser:
            return qs
        return qs.filter(recipient=user)


class MarkNotificationReadView(APIView):
    """PATCH /notifications/{pk}/read/ — mark a single notification as read."""
    permission_classes = [IsAuthenticated, IsNotificationOwner]

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        self.check_object_permissions(request, notification)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


class MarkAllReadView(APIView):
    """POST /notifications/read-all/ — mark all unread notifications as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)
        return Response({"detail": "All notifications marked as read."}, status=status.HTTP_200_OK)


class UnreadCountView(APIView):
    """GET /notifications/unread-count/ — returns unread notification count."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({"unread_count": count}, status=status.HTTP_200_OK)


class AdminSendNotificationView(APIView):
    """POST /notifications/admin/send/ — admin manually sends a notification."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = AdminSendNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recipient = serializer.resolve_recipient()
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=serializer.validated_data['notification_type'],
            title=serializer.validated_data['title'],
            message=serializer.validated_data['message'],
            is_read=False,
        )
        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_201_CREATED,
        )
