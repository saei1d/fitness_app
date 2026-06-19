from decimal import Decimal

from django.db import transaction
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.client.gateway import PaymentGatewayError, request_payment
from finance.client.purchase import _finalize_paid_purchase
from finance.models import Purchase, Transaction
from finance.serializers import PurchaseSerializer, TransactionSerializer
from packages.models import Package


@extend_schema(tags=['purchase'])
class CreatePendingPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, package_id):
        package = Package.objects.filter(id=package_id).first()
        if not package:
            return Response({'error': 'Package not found'}, status=404)

        discount_code = request.data.get('discount_code')
        payload = {'package': package.id, 'payment_status': 'pending'}
        if discount_code:
            payload['discount_code'] = discount_code

        serializer = PurchaseSerializer(
            data=payload,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            with transaction.atomic():
                purchase = serializer.save()
                trans = Transaction.objects.create(
                    amount=purchase.final_amount,
                    purchase=purchase,
                    type='credit',
                    status='pending',
                    description=f'Pending payment for purchase #{purchase.id}',
                )

            if purchase.final_amount <= Decimal('0'):
                with transaction.atomic():
                    purchase = Purchase.objects.select_for_update().get(pk=purchase.pk)
                    trans = Transaction.objects.select_for_update().get(pk=trans.pk)
                    _finalize_paid_purchase(purchase=purchase, transaction_obj=trans)

                return Response({
                    'message': 'Free purchase completed',
                    'payment_required': False,
                    'payment_url': None,
                    'purchase': PurchaseSerializer(purchase).data,
                    'transaction': TransactionSerializer(trans).data,
                }, status=201)

            callback_url = request.build_absolute_uri(reverse('api-v1:payment-callback'))
            gateway_result = request_payment(
                amount=purchase.final_amount,
                description=f'Payment for purchase #{purchase.id}',
                callback_url=callback_url,
                metadata={
                    'mobile': request.user.phone,
                },
            )

            with transaction.atomic():
                purchase = Purchase.objects.select_for_update().get(pk=purchase.pk)
                trans = Transaction.objects.select_for_update().get(pk=trans.pk)
                purchase.payment_authority = gateway_result.authority
                purchase.save(update_fields=['payment_authority'])
                trans.description = f'Awaiting payment for purchase #{purchase.id}'
                trans.save(update_fields=['description'])

            return Response({
                'message': 'Pending purchase created',
                'payment_required': True,
                'payment_url': gateway_result.payment_url,
                'authority': gateway_result.authority,
                'callback_url': callback_url,
                'purchase': PurchaseSerializer(purchase).data,
                'transaction': TransactionSerializer(trans).data,
            }, status=201)

        except PaymentGatewayError as exc:
            with transaction.atomic():
                purchase = Purchase.objects.select_for_update().get(pk=purchase.pk)
                trans = Transaction.objects.select_for_update().get(pk=trans.pk)
                purchase.payment_status = 'failed'
                purchase.save(update_fields=['payment_status'])
                trans.status = 'failed'
                trans.description = f'Gateway request failed for purchase #{purchase.id}: {exc}'
                trans.save(update_fields=['status', 'description'])

            return Response({'error': str(exc)}, status=502)
        except Exception as exc:
            return Response({'error': str(exc)}, status=400)
