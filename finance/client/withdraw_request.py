from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from finance.models import WithdrawRequest
from finance.serializers import WithdrawRequestSerializer
from rest_framework.permissions import IsAdminUser
from django.db import transaction
from finance.serializers import AdminWithdrawUpdateSerializer
from finance.models import Wallet, Transaction


class WithdrawRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawRequestSerializer
    

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        withdraw_requests = WithdrawRequest.objects.filter(user=request.user)
        serializer = self.serializer_class(withdraw_requests, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminWithdrawRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AdminWithdrawUpdateSerializer

    def patch(self, request, pk):
        try:
            instance = WithdrawRequest.objects.select_related('wallet', 'user').get(pk=pk)
        except WithdrawRequest.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(instance, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data.get('status')

        if new_status == 'completed':
            with transaction.atomic():
                wallet = instance.wallet
                amount = instance.amount
                if amount > wallet.balance:
                    return Response({"amount": "Amount exceeds wallet balance at completion"}, status=status.HTTP_400_BAD_REQUEST)
                wallet.balance -= amount
                wallet.save()
                Transaction.objects.create(
                    wallet=wallet,
                    amount=amount,
                    type='debit',
                    status='completed',
                    description=f"Withdrawal completed. Request #{instance.id}. " + request.data.get('admin_message', '')
                )
                serializer.save()
        else:
            serializer.save()

        return Response(self.serializer_class(instance).data, status=status.HTTP_200_OK)
    