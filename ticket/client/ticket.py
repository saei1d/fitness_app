from rest_framework import viewsets, permissions, status
from django.db import models
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.decorators import action
from ..models import Ticket, TicketMessage
from ..serializers import TicketSerializer, TicketMessageSerializer, TicketDetailSerializer


class IsTicketCreatorOrStaff(permissions.BasePermission):
    """فقط سازنده‌ی تیکت یا کاربر staff به تیکت دسترسی دارند"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return (
                request.user and request.user.is_authenticated and (
                    request.user.is_staff or
                    obj.creator_id == request.user.id
                )
            )
        # Write operations: only staff can modify tickets
        return (
            request.user and request.user.is_authenticated and request.user.is_staff
        )


class IsSuperUserOrReadOnly(permissions.BasePermission):
    """فقط سوپر یوزر می‌تواند حذف کند"""

    def has_permission(self, request, view):
        if request.method == 'DELETE':
            return request.user and request.user.is_authenticated and request.user.is_superuser
        return request.user and request.user.is_authenticated


@extend_schema(tags=['Ticket'])
class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsTicketCreatorOrStaff, IsSuperUserOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Ticket.objects.all().select_related('creator', 'admin').prefetch_related('messages__author')
        # Regular users can only see their own tickets
        return Ticket.objects.filter(creator=user).select_related('creator', 'admin').prefetch_related('messages__author')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TicketDetailSerializer
        if self.action in ['update', 'partial_update']:
            # Disable update operations
            return None
        return TicketSerializer

    def update(self, request, *args, **kwargs):
        """Disable ticket updates"""
        return Response(
            {'error': 'تیکت قابل ویرایش نیست'}, 
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        """Disable ticket partial updates"""
        return Response(
            {'error': 'تیکت قابل ویرایش نیست'}, 
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @extend_schema(
        summary='تغییر وضعیت تیکت',
        description='تغییر وضعیت تیکت (کاربران عادی فقط می‌توانند باز را ببندند، ادمین‌ها همه وضعیت‌ها را می‌توانند تغییر دهند)',
        request={
            'type': 'object',
            'properties': {
                'status': {'type': 'string', 'description': 'وضعیت جدید تیکت'}
            },
            'required': ['status']
        },
        responses={200: TicketSerializer, 400: dict, 403: dict}
    )
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def change_status(self, request, pk=None):
        """Allow status changes with restrictions"""
        ticket = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'وضعیت جدید الزامی است'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if status is valid
        valid_statuses = [choice[0] for choice in Ticket.Status.choices]
        if new_status not in valid_statuses:
            return Response(
                {'error': 'وضعیت نامعتبر است'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Regular users can only close open tickets
        if not request.user.is_staff:
            if ticket.status != Ticket.Status.OPEN:
                return Response(
                    {'error': 'فقط تیکت‌های باز قابل بستن هستند'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            if new_status != Ticket.Status.CLOSED:
                return Response(
                    {'error': 'کاربران عادی فقط می‌توانند تیکت را ببندند'}, 
                    status=status.HTTP_403_FORBIDDEN
                )

        ticket.status = new_status
        ticket.save()
        
        serializer = self.get_serializer(ticket)
        return Response(serializer.data)


@extend_schema(tags=['TicketMessage'])
class TicketMessageViewSet(viewsets.ModelViewSet):
    serializer_class = TicketMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base_qs = TicketMessage.objects.select_related('ticket', 'author', 'ticket__creator', 'ticket__admin')
        if user.is_staff:
            return base_qs
        # Regular users can only see messages of their own tickets
        return base_qs.filter(ticket__creator=user)


    

