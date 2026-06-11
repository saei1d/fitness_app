import random

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from finance.models import AdminWallet, Purchase, Transaction, Wallet
from finance.serializers import PurchaseSerializer


def generate_buyer_code():
    while True:
        code = ''.join(random.choices('0123456789', k=6))
        if not Purchase.objects.filter(buyer_code=code).exists():
            return code


def verify_payment_gateway(transaction_obj, request):
    """Placeholder gateway verification hook.

    In production this function should call the PSP with the authority/reference
    supplied by the frontend. For local/manual testing, the caller must submit
    payment_verified=true so payment cannot be finalized accidentally.
    """
    return request.data.get('payment_verified') is True


@extend_schema(tags=['purchase'])
class FinalizePurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: dict},
        description="تایید پرداخت و واریز مبلغ به حساب ادمین"
    )
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response({'error': 'transaction_id is required'}, status=400)

        try:
            with transaction.atomic():
                trans = Transaction.objects.select_for_update().select_related('purchase').get(
                    id=transaction_id,
                    purchase__user=request.user,
                )
                purchase = Purchase.objects.select_for_update().get(id=trans.purchase_id, user=request.user)

                if purchase.payment_status != 'pending':
                    return Response({'error': 'Purchase is not in pending status'}, status=400)
                if trans.status != 'pending':
                    return Response({'error': 'Transaction is not in pending status'}, status=400)

                if not verify_payment_gateway(trans, request):
                    purchase.payment_status = 'failed'
                    purchase.save(update_fields=['payment_status'])
                    trans.status = 'failed'
                    trans.description = f'Payment verification failed for purchase #{purchase.id}'
                    trans.save(update_fields=['status', 'description'])
                    return Response({'error': 'Payment verification failed'}, status=400)

                purchase.payment_status = 'paid'
                purchase.buyer_code = generate_buyer_code()
                purchase.save(update_fields=['payment_status', 'buyer_code'])

                admin_wallet, _ = AdminWallet.objects.select_for_update().get_or_create(
                    id=1,
                    defaults={'balance': 0}
                )

                trans.admin_wallet = admin_wallet
                trans.amount = purchase.final_amount
                trans.type = 'credit'
                trans.status = 'completed'
                trans.description = f"پرداخت خرید #{purchase.id} - کاربر: {purchase.user.phone}"
                trans.save(update_fields=['admin_wallet', 'amount', 'type', 'status', 'description'])

                AdminWallet.objects.filter(pk=admin_wallet.pk).update(balance=F('balance') + purchase.final_amount)
                admin_wallet.refresh_from_db(fields=['balance'])

                return Response({
                    'message': 'Payment confirmed and transferred to admin wallet',
                    'buyer_code': purchase.buyer_code,
                    'purchase': PurchaseSerializer(purchase).data
                }, status=200)

        except Transaction.DoesNotExist:
            return Response({'error': 'Transaction not found or not authorized'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)


@extend_schema(tags=['purchase'])
class VerifyPurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: dict},
        description="تایید خرید توسط صاحب باشگاه و واریز مبلغ به حسابش"
    )
    def post(self, request):
        buyer_code = request.data.get('buyer_code')
        if not buyer_code:
            return Response({'error': 'buyer_code is required'}, status=400)

        if request.user.role != 'owner':
            return Response({'error': 'Only gym owners can verify purchases'}, status=403)

        try:
            with transaction.atomic():
                purchase = Purchase.objects.select_for_update().select_related(
                    'package__group_package__gym__owner'
                ).filter(
                    buyer_code=buyer_code,
                    payment_status='paid',
                    verification_status='pending',
                ).first()

                if not purchase:
                    return Response({'error': 'Purchase not found or already processed'}, status=404)

                if purchase.package.group_package.gym.owner != request.user:
                    return Response({'error': 'This purchase does not belong to your gym'}, status=403)

                admin_wallet = AdminWallet.objects.select_for_update().get(id=1)
                if admin_wallet.balance < purchase.net_amount:
                    return Response({'error': 'موجودی کیف پول ادمین کافی نیست'}, status=400)

                wallet, _ = Wallet.objects.select_for_update().get_or_create(
                    owner=request.user,
                    defaults={'balance': 0}
                )

                purchase.verification_status = 'verified'
                purchase.verified_at = timezone.now()
                purchase.verified_by = request.user
                purchase.save(update_fields=['verification_status', 'verified_at', 'verified_by'])

                Transaction.objects.create(
                    wallet=wallet,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='credit',
                    status='completed',
                    description=f"تایید خرید #{purchase.id} - کد: {buyer_code}",
                )

                Transaction.objects.create(
                    admin_wallet=admin_wallet,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='debit',
                    status='completed',
                    description=f"پرداخت سهم باشگاه برای خرید #{purchase.id} - کد: {buyer_code}",
                )

                Wallet.objects.filter(pk=wallet.pk).update(balance=F('balance') + purchase.net_amount)
                AdminWallet.objects.filter(pk=admin_wallet.pk).update(balance=F('balance') - purchase.net_amount)

                return Response({
                    'message': 'Purchase verified successfully',
                    'purchase': PurchaseSerializer(purchase).data
                }, status=200)

        except AdminWallet.DoesNotExist:
            return Response({'error': 'Admin wallet not found'}, status=500)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
