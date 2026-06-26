from rest_framework import viewsets, permissions, status
from django.db.models import Q
from django.utils.dateparse import parse_datetime
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


@extend_schema(tags=['Support Requests'])
class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsTicketCreatorOrStaff, IsSuperUserOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Ticket.objects.select_related('creator', 'admin').prefetch_related('messages__author')

        if user.is_staff:
            pass
        else:
            queryset = queryset.filter(creator=user)

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        subject = self.request.query_params.get('subject')
        if subject:
            queryset = queryset.filter(subject__icontains=subject)

        creator_phone = self.request.query_params.get('creator_phone')
        if creator_phone:
            queryset = queryset.filter(creator__phone__icontains=creator_phone)

        creator_name = self.request.query_params.get('creator_name')
        if creator_name:
            queryset = queryset.filter(creator__full_name__icontains=creator_name)

        admin_id = self.request.query_params.get('admin_id')
        if admin_id:
            queryset = queryset.filter(admin_id=admin_id)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(subject__icontains=search)
                | Q(creator__phone__icontains=search)
                | Q(creator__full_name__icontains=search)
                | Q(messages__message__icontains=search)
            )

        created_from = self.request.query_params.get('created_from')
        if created_from:
            dt = parse_datetime(created_from)
            if dt:
                queryset = queryset.filter(created_at__gte=dt)

        created_to = self.request.query_params.get('created_to')
        if created_to:
            dt = parse_datetime(created_to)
            if dt:
                queryset = queryset.filter(created_at__lte=dt)

        updated_from = self.request.query_params.get('updated_from')
        if updated_from:
            dt = parse_datetime(updated_from)
            if dt:
                queryset = queryset.filter(updated_at__gte=dt)

        updated_to = self.request.query_params.get('updated_to')
        if updated_to:
            dt = parse_datetime(updated_to)
            if dt:
                queryset = queryset.filter(updated_at__lte=dt)

        ordering = self.request.query_params.get('ordering', '-created_at')
        allowed_ordering = {
            'created_at', '-created_at',
            'updated_at', '-updated_at',
            'status', '-status',
            'subject', '-subject',
        }
        if ordering not in allowed_ordering:
            ordering = '-created_at'

        return queryset.distinct().order_by(ordering)

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
    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated], url_path='status')
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


@extend_schema(tags=['Support Replies'])
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


    

