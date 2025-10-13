from rest_framework import viewsets, permissions
from django.db import models
from drf_spectacular.utils import extend_schema
from ..models import Ticket, TicketMessage
from ..serializers import TicketSerializer, TicketMessageSerializer


class IsTicketParticipantOrStaff(permissions.BasePermission):
    """فقط سازنده‌ی تیکت، ادمین اختصاص‌داده‌شده یا کاربر staff به تیکت دسترسی دارند"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return (
                request.user and request.user.is_authenticated and (
                    request.user.is_staff or
                    obj.creator_id == request.user.id or
                    (obj.admin_id == request.user.id if obj.admin_id else False)
                )
            )
        # Write operations: same participants
        return (
            request.user and request.user.is_authenticated and (
                request.user.is_staff or
                obj.creator_id == request.user.id or
                (obj.admin_id == request.user.id if obj.admin_id else False)
            )
        )


@extend_schema(tags=['Ticket'])
class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsTicketParticipantOrStaff]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all().select_related('creator', 'admin')
        return Ticket.objects.filter(
            models.Q(creator=user) | models.Q(admin=user)
        ).select_related('creator', 'admin')


@extend_schema(tags=['TicketMessage'])
class TicketMessageViewSet(viewsets.ModelViewSet):
    serializer_class = TicketMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = TicketMessage.objects.select_related('ticket', 'author', 'ticket__creator', 'ticket__admin')
        if user.is_staff:
            return base_qs
        # Limit to messages of tickets where user participates
        return base_qs.filter(models.Q(ticket__creator=user) | models.Q(ticket__admin=user))


    

