from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import Purchase
from finance.serializers import PurchaseHistorySerializer


@extend_schema(tags=['purchase'])
class PurchaseHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = Purchase.objects.select_related(
            'user',
            'package__group_package__gym',
            'discount_code',
            'verified_by',
        )

        if not user.is_staff and getattr(user, 'role', None) != 'admin':
            queryset = queryset.filter(user=user)
        else:
            user_id = request.query_params.get('user_id')
            if user_id:
                queryset = queryset.filter(user_id=user_id)

            phone = request.query_params.get('phone')
            if phone:
                queryset = queryset.filter(user__phone__icontains=phone)

            gym_id = request.query_params.get('gym_id')
            if gym_id:
                queryset = queryset.filter(package__group_package__gym_id=gym_id)

        payment_status = request.query_params.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)

        verification_status = request.query_params.get('verification_status')
        if verification_status:
            queryset = queryset.filter(verification_status=verification_status)

        membership_status = request.query_params.get('membership_status')
        if membership_status:
            now = timezone.now()
            filtered_ids = []
            for purchase in queryset:
                end_date = purchase.expire_date
                if end_date is None and purchase.verified_at is not None:
                    end_date = purchase.verified_at + timedelta(days=purchase.package.duration)

                is_active = (
                    purchase.payment_status == 'paid'
                    and purchase.verification_status == 'verified'
                    and end_date is not None
                    and end_date >= now
                )

                if membership_status == 'active' and is_active:
                    filtered_ids.append(purchase.id)
                elif membership_status == 'inactive' and not is_active:
                    filtered_ids.append(purchase.id)
                elif membership_status == 'expired' and purchase.payment_status == 'paid' and purchase.verification_status == 'verified' and end_date is not None and end_date < now:
                    filtered_ids.append(purchase.id)
                elif membership_status == 'pending_payment' and purchase.payment_status != 'paid':
                    filtered_ids.append(purchase.id)
                elif membership_status == 'pending_verification' and purchase.payment_status == 'paid' and purchase.verification_status != 'verified':
                    filtered_ids.append(purchase.id)
                elif membership_status == 'rejected' and purchase.verification_status == 'rejected':
                    filtered_ids.append(purchase.id)
            queryset = queryset.filter(id__in=filtered_ids)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__phone__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(package__title__icontains=search)
                | Q(package__group_package__gym__name__icontains=search)
                | Q(buyer_code__icontains=search)
                | Q(discount_code__code__icontains=search)
            )

        ordering = request.query_params.get('ordering', '-purchase_date')
        allowed_ordering = {
            'purchase_date', '-purchase_date',
            'verified_at', '-verified_at',
            'expire_date', '-expire_date',
            'final_amount', '-final_amount',
            'id', '-id',
        }
        if ordering not in allowed_ordering:
            ordering = '-purchase_date'

        queryset = queryset.order_by(ordering)

        serializer = PurchaseHistorySerializer(queryset, many=True, context={'request': request, 'now': timezone.now()})
        return Response(serializer.data)
