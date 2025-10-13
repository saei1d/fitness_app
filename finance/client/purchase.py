from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from finance.models import Purchase, Wallet, AdminWallet, Transaction
from finance.serializers import PurchaseSerializer


@extend_schema(tags=['purchase'])
class FinalizePurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: dict},
        description="فقط کافیه transaction_id رو بفرستی "
    )
    def post(self, request):
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response({'error': 'transaction_id is required'}, status=400)

        trans = Transaction.objects.get(id=transaction_id)

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
        # fill payment id
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
                purchase.save()

                # پیدا کردن یا ساختن والت صاحب باشگاه
                gym_owner = purchase.package.gym.owner
                wallet, _ = Wallet.objects.get_or_create(
                    owner=gym_owner,
                    defaults={'balance': 0}
                )

                # پیدا کردن یا ساختن والت ادمین
                admin_wallet, _ = AdminWallet.objects.get_or_create(
                    id=1,
                    defaults={'balance': 0}
                )

                # تراکنش‌ها:
                # 1️⃣ واریز سهم باشگاه
                Transaction.objects.create(
                    wallet=wallet,
                    admin_wallet=None,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='debit',
                    created_at=timezone.now()
                )

                # 2️⃣ واریز کمیسیون به ادمین
                Transaction.objects.create(
                    wallet=None,
                    admin_wallet=admin_wallet,
                    purchase=purchase,
                    amount=purchase.commission_amount,
                    type='debit',
                    created_at=timezone.now()
                )

                # به‌روزرسانی موجودی‌ها
                wallet.balance += purchase.net_amount
                wallet.save()

                admin_wallet.balance += purchase.commission_amount
                admin_wallet.save()

                return Response({
                    'message': 'Purchase finalized successfully',
                    'purchase': PurchaseSerializer(purchase).data
                }, status=200)

        except Exception as e:
            return Response({'error': str(e)}, status=500)
