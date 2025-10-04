from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from ..models import Wallet, AdminWallet, Transaction, Purchase
from ..serializers import PurchaseSerializer


class FinalizePurchaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, purchase_id):
        # پیدا کردن پیش‌فاکتور
        purchase = Purchase.objects.filter(id=purchase_id, user=request.user).first()
        if not purchase:
            return Response({'error': 'Purchase not found or not authorized'}, status=404)

        if purchase.payment_status != 'pending':
            return Response({'error': 'Purchase is not in pending status'}, status=400)

        # فرض: اعتبارسنجی پرداخت از درگاه (مثلاً ZarinPal)
        transaction_id = request.data.get('transaction_id')
        if not transaction_id:
            return Response({'error': 'Transaction ID required'}, status=400)

        # اینجا باید درگاه پرداخت رو verify کنید (مثلاً با API ZarinPal)
        # برای مثال فرض می‌کنیم پرداخت معتبره
        is_payment_valid = True  # جای این خط باید API درگاه رو فراخوانی کنید

        if not is_payment_valid:
            purchase.payment_status = 'failed'
            purchase.save()
            return Response({'error': 'Payment verification failed'}, status=400)

        try:
            with transaction.atomic():
                # تغییر وضعیت به paid
                purchase.payment_status = 'paid'
                purchase.save()

                # پیدا کردن یا ایجاد والت صاحب باشگاه
                gym_owner = purchase.package.gym.owner
                wallet, created = Wallet.objects.get_or_create(
                    owner=gym_owner,
                    defaults={'balance': 0}
                )

                # پیدا کردن یا ایجاد والت ادمین
                admin_wallet, created = AdminWallet.objects.get_or_create(
                    id=1,  # فرض: فقط یک والت ادمین داریم
                    defaults={'balance': 0}
                )

                # تراکنش‌ها
                # 1. Credit: پرداخت کاربر
                Transaction.objects.create(
                    wallet=None,  # برای کاربر مستقیم والت نداریم
                    admin_wallet=None,
                    purchase=purchase,
                    amount=purchase.total_amount,
                    type='credit',
                    created_at=timezone.now()
                )

                # 2. Debit: واریز به والت صاحب باشگاه
                Transaction.objects.create(
                    wallet=wallet,
                    admin_wallet=None,
                    purchase=purchase,
                    amount=purchase.net_amount,
                    type='debit',
                    created_at=timezone.now()
                )

                # 3. Debit: واریز کمیسیون به والت ادمین
                Transaction.objects.create(
                    wallet=None,
                    admin_wallet=admin_wallet,
                    purchase=purchase,
                    amount=purchase.commission_amount,
                    type='debit',
                    created_at=timezone.now()
                )

                # به‌روزرسانی والت‌ها
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