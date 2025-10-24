from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from finance.models import Purchase, Wallet, AdminWallet, Transaction
from finance.serializers import PurchaseSerializer
import random


def generate_buyer_code():
    return ''.join(random.choices('0123456789', k=6))

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
            trans = Transaction.objects.get(id=transaction_id)
        except Transaction.DoesNotExist:
            return Response({'error': 'Transaction not found'}, status=404)

        purchase_id = trans.purchase_id
        if not purchase_id:
            return Response({'error': 'purchase_id is required'}, status=400)

        # پیدا کردن خرید مورد نظر
        purchase = Purchase.objects.filter(id=purchase_id, user=request.user).first()
        if not purchase:
            return Response({'error': 'Purchase not found or not authorized'}, status=404)

        if purchase.payment_status != 'pending':
            return Response({'error': 'Purchase is not in pending status'}, status=400)

        # بررسی transaction_id (مثلاً از زرین‌پال)
        # فرض می‌کنیم پرداخت تایید شده است
        is_payment_valid = True
        if not is_payment_valid:
            purchase.payment_status = 'failed'
            purchase.save()
            return Response({'error': 'Payment verification failed'}, status=400)

        try:
            with transaction.atomic():
                # تغییر وضعیت خرید به "پرداخت شده"
                purchase.payment_status = 'paid'
                buyer_code_genrate = generate_buyer_code()
                purchase.buyer_code = buyer_code_genrate
                purchase.save()

                # پیدا کردن یا ساختن والت ادمین
                admin_wallet, _ = AdminWallet.objects.get_or_create(
                    id=1,
                    defaults={'balance': 0}
                )

                # واریز کل مبلغ به حساب ادمین
                Transaction.objects.create(
                    wallet=None,
                    admin_wallet=admin_wallet,
                    purchase=purchase,
                    amount=purchase.total_amount,
                    type='credit',
                    status='completed',
                    description=f"پرداخت خرید #{purchase.id} - کاربر: {purchase.user.phone}",
                    created_at=timezone.now()
                )

                # به‌روزرسانی موجودی ادمین
                admin_wallet.balance += purchase.total_amount
                admin_wallet.save()

                return Response({
                    'message': 'Payment confirmed and transferred to admin wallet',
                    'buyer_code': buyer_code_genrate,
                    'purchase': PurchaseSerializer(purchase).data
                }, status=200)

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

        # بررسی نقش کاربر
        if request.user.role != 'owner':
            return Response({'error': 'Only gym owners can verify purchases'}, status=403)

        # پیدا کردن خرید با buyer_code
        purchase = Purchase.objects.filter(
            buyer_code=buyer_code,
            verification_status='pending'
        ).first()

        if not purchase:
            return Response({'error': 'Purchase not found or already processed'}, status=404)

        # بررسی اینکه خرید متعلق به باشگاه این owner است
        if purchase.package.group_package.gym.owner != request.user:
            return Response({'error': 'This purchase does not belong to your gym'}, status=403)

        try:
            with transaction.atomic():
                # تغییر وضعیت تایید
                purchase.verification_status = 'verified'
                purchase.verified_at = timezone.now()
                purchase.verified_by = request.user
                purchase.save()

                # پیدا کردن یا ساختن والت صاحب باشگاه
                gym_owner = purchase.package.group_package.gym.owner
                wallet, _ = Wallet.objects.get_or_create(
                    owner=gym_owner,
                    defaults={'balance': 0}
                )

                # پیدا کردن کیف پول ادمین
                admin_wallet = AdminWallet.objects.get(id=1)
                
                # بررسی موجودی کافی در کیف پول ادمین
                if admin_wallet.balance < purchase.net_amount:
                    return Response({
                        'error': 'موجودی کیف پول ادمین کافی نیست'
                    }, status=400)

                # واریز سهم باشگاه (مبلغ خالص)
                Transaction.objects.create(
                    wallet=wallet,
                    admin_wallet=None,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='credit',
                    status='completed',
                    description=f"تایید خرید #{purchase.id} - کد: {buyer_code}",
                    created_at=timezone.now()
                )

                # کسر مبلغ خالص از کیف پول ادمین
                Transaction.objects.create(
                    wallet=None,
                    admin_wallet=admin_wallet,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='debit',
                    status='completed',
                    description=f"پرداخت سهم باشگاه برای خرید #{purchase.id} - کد: {buyer_code}",
                    created_at=timezone.now()
                )

                # به‌روزرسانی موجودی والت باشگاه
                wallet.balance += purchase.net_amount
                wallet.save()
                
                # کسر مبلغ خالص از کیف پول ادمین
                admin_wallet.balance -= purchase.net_amount
                admin_wallet.save()

                return Response({
                    'message': 'Purchase verified successfully',
                    'purchase': PurchaseSerializer(purchase).data
                }, status=200)

        except Exception as e:
            return Response({'error': str(e)}, status=500)
