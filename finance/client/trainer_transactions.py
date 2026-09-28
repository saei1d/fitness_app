from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from finance.models import Transaction, TrainerWallet
from finance.serializers import TransactionSerializer


@extend_schema(tags=['Transaction'])
class TrainerTransactionListView(APIView):
    """لیست تراکنش‌های مربی"""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: TransactionSerializer(many=True)},
        summary='لیست تراکنش‌های مربی',
        description='نمایش لیست تراکنش‌های کیف پول مربی'
    )
    def get(self, request):
        if request.user.role != 'trainer':
            return Response(
                {'error': 'این endpoint فقط برای مربیان است'},
                status=status.HTTP_403_FORBIDDEN
            )

        from trainers.models import Trainer
        try:
            trainer = Trainer.objects.get(user=request.user)
            wallet = TrainerWallet.objects.get(trainer=trainer)
            transactions = Transaction.objects.filter(trainer_wallet=wallet).select_related('trainer_wallet__trainer', 'admin_wallet', 'purchase').order_by('-id')
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Trainer.DoesNotExist:
            return Response(
                {'error': 'مربی‌گری برای شما یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )
        except TrainerWallet.DoesNotExist:
            return Response(
                {'error': 'کیف پولی برای شما یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )
