from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import Purchase
from finance.serializers import GymMemberSerializer


class IsOwnerOrAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or getattr(request.user, 'role', None) in {'owner', 'admin'})
        )


@extend_schema(tags=['member'])
class GymMemberListView(APIView):
    permission_classes = [IsOwnerOrAdminUser]

    def get(self, request):
        user = request.user
        queryset = Purchase.objects.select_related(
            'user',
            'package__group_package__gym',
            'verified_by',
        )

        if not (user.is_staff or getattr(user, 'role', None) == 'admin'):
            queryset = queryset.filter(package__group_package__gym__owner=user)

        gym_id = request.query_params.get('gym_id')
        if gym_id:
            queryset = queryset.filter(package__group_package__gym_id=gym_id)

        payment_status = request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        verification_status = request.query_params.get('verification_status')
        if verification_status:
            queryset = queryset.filter(verification_status=verification_status)

        phone = request.query_params.get('phone')
        if phone:
            queryset = queryset.filter(user__phone__icontains=phone)

        name = request.query_params.get('name')
        if name:
            queryset = queryset.filter(user__full_name__icontains=name)

        package_title = request.query_params.get('package_title')
        if package_title:
            queryset = queryset.filter(package__title__icontains=package_title)

        buyer_code = request.query_params.get('buyer_code')
        if buyer_code:
            queryset = queryset.filter(buyer_code__icontains=buyer_code)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__phone__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(package__title__icontains=search)
                | Q(package__group_package__gym__name__icontains=search)
                | Q(buyer_code__icontains=search)
            )

        queryset = queryset.order_by(
            'package__group_package__gym_id',
            'user_id',
            '-verified_at',
            '-purchase_date',
            '-id',
        )

        now = timezone.now()
        grouped_memberships = {}
        for purchase in queryset:
            key = (purchase.user_id, purchase.package.group_package.gym_id)
            grouped_memberships.setdefault(key, []).append(purchase)

        def is_active_membership(purchase):
            return (
                purchase.payment_status == 'paid'
                and purchase.verification_status == 'verified'
                and purchase.expire_date is not None
                and purchase.expire_date >= now
            )

        latest_memberships = []
        for purchases in grouped_memberships.values():
            active_purchases = [purchase for purchase in purchases if is_active_membership(purchase)]
            if active_purchases:
                latest_memberships.append(active_purchases[0])
            else:
                latest_memberships.append(purchases[0])

        status_filter = request.query_params.get('membership_status') or request.query_params.get('status')

        if status_filter in {'active', 'inactive'}:
            filtered = []
            for purchase in latest_memberships:
                is_active = is_active_membership(purchase)
                if status_filter == 'active' and is_active:
                    filtered.append(purchase)
                if status_filter == 'inactive' and not is_active:
                    filtered.append(purchase)
            latest_memberships = filtered

        serializer = GymMemberSerializer(latest_memberships, many=True, context={'request': request, 'now': now})
        return Response(serializer.data)
