from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.client.gateway import PaymentGatewayError, request_payment
from finance.client.purchase import _finalize_paid_purchase
from finance.models import Purchase, Transaction
from finance.serializers import PurchaseSerializer, TransactionSerializer
from packages.models import Package


@extend_schema(
    tags=['purchase'],
    summary="Create a pending purchase",
    description="Create a pending purchase for a package and get payment link if needed. Accepts optional discount_code.",
    examples=[
        OpenApiExample(
            'Request with discount code',
            value={'discount_code': 'SUMMER2024'},
            request_only=True,
        ),
        OpenApiExample(
            'Request without discount code',
            value={},
            request_only=True,
        ),
    ],
    responses={
        201: OpenApiResponse(
            description="Pending purchase created or free purchase completed",
            examples=[
                OpenApiExample(
                    'Payment required (with discount)',
                    value={
                        'message': 'Pending purchase created',
                        'payment_required': True,
                        'payment_url': 'https://payment-gateway.example.com/pay/12345',
                        'authority': '00000000000000000000000000012345',
                        'callback_url': 'https://your-domain.com/api/finance/payment-callback/',
                        'purchase': {
                            'id': 1,
                            'user': 1,
                            'package': 5,
                            'buyer_code': None,
                            'payment_authority': '00000000000000000000000000012345',
                            'payment_reference_id': None,
                            'purchase_date': '2024-07-08T12:34:56Z',
                            'expire_date': None,
                            'payment_status': 'pending',
                            'verification_status': 'pending',
                            'total_amount': '100000.00',
                            'commission_amount': '10000.00',
                            'net_amount': '80000.00',
                            'verified_at': None,
                            'verified_by': None,
                            'discount_code': 1,
                            'final_amount': '85000.00',
                            'admin_notes': 'قیمت اصلی: 100000.00 تومان\nتخفیف پکیج: (5.0% از club)\nکد تخفیف: SUMMER2024 (10.0% از admin)\nقیمت نهایی: 85000.00 تومان\nکمیسیون ادمین: 5000.00 تومان\nسهم باشگاه: 80000.00 تومان',
                            'user_name': 'John Doe',
                            'user_phone': '09123456789',
                            'package_title': 'Monthly Gym Membership',
                            'verified_by_name': None,
                            'code_expire_date': '2024-07-15 12:34',
                            'is_code_expired': False,
                        },
                        'transaction': {
                            'id': 1,
                            'wallet': None,
                            'admin_wallet': None,
                            'purchase': 1,
                            'amount': '85000.00',
                            'type': 'credit',
                            'status': 'pending',
                            'payment_id': None,
                            'description': 'Awaiting payment for purchase #1',
                            'created_at': '2024-07-08T12:34:56Z',
                        },
                    },
                ),
                OpenApiExample(
                    'Free purchase completed',
                    value={
                        'message': 'Free purchase completed',
                        'payment_required': False,
                        'payment_url': None,
                        'purchase': {
                            'id': 2,
                            'user': 1,
                            'package': 10,
                            'buyer_code': '123456',
                            'payment_authority': None,
                            'payment_reference_id': None,
                            'purchase_date': '2024-07-08T12:40:00Z',
                            'expire_date': None,
                            'payment_status': 'paid',
                            'verification_status': 'pending',
                            'total_amount': '50000.00',
                            'commission_amount': '5000.00',
                            'net_amount': '40000.00',
                            'verified_at': None,
                            'verified_by': None,
                            'discount_code': 2,
                            'final_amount': '0.00',
                            'admin_notes': 'قیمت اصلی: 50000.00 تومان\nکد تخفیف: FREETRIAL (100.0% از admin)\nقیمت نهایی: 0.00 تومان\nکمیسیون ادمین: 0.00 تومان\nسهم باشگاه: 0.00 تومان',
                            'user_name': 'John Doe',
                            'user_phone': '09123456789',
                            'package_title': 'Free Trial Membership',
                            'verified_by_name': None,
                            'code_expire_date': '2024-07-15 12:40',
                            'is_code_expired': False,
                        },
                        'transaction': {
                            'id': 2,
                            'wallet': None,
                            'admin_wallet': 1,
                            'purchase': 2,
                            'amount': '0.00',
                            'type': 'credit',
                            'status': 'completed',
                            'payment_id': None,
                            'description': 'Purchase #2 paid by 09123456789',
                            'created_at': '2024-07-08T12:40:00Z',
                        },
                    },
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Bad request (invalid package, discount code, or other errors)",
            examples=[
                OpenApiExample(
                    'Invalid discount code',
                    value={'discount_code': ['کد تخفیف معتبر نیست یا ظرفیت آن تمام شده است']},
                ),
                OpenApiExample(
                    'Package not found',
                    value={'error': 'Package not found'},
                ),
            ],
        ),
        404: OpenApiResponse(
            description="Package not found",
            examples=[
                OpenApiExample(
                    'Package not found',
                    value={'error': 'Package not found'},
                ),
            ],
        ),
        502: OpenApiResponse(
            description="Payment gateway error",
            examples=[
                OpenApiExample(
                    'Gateway error',
                    value={'error': 'Gateway error message'},
                ),
            ],
        ),
    },
)
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

            callback_base_url = getattr(settings, 'PAYMENT_GATEWAY_CALLBACK_BASE_URL', '').strip()
            if callback_base_url:
                callback_url = f"{callback_base_url.rstrip('/')}{reverse('api-v1:payment-callback')}"
            else:
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
