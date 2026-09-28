from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from finance.models import TrainerWithdrawRequest, TrainerWallet
from finance.serializers import TrainerWithdrawRequestSerializer


@extend_schema(tags=['Withdraw Request'])
class TrainerWithdrawRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TrainerWithdrawRequestSerializer

    @extend_schema(
        request=TrainerWithdrawRequestSerializer,
        responses={201: TrainerWithdrawRequestSerializer},
        summary='ایجاد درخواست برداشت مربی',
        description='ایجاد درخواست برداشت برای کاربران trainer'
    )
    def post(self, request):
        if request.user.role != 'trainer':
            return Response(
                {'error': 'این endpoint فقط برای مربیان است'},
                status=status.HTTP_403_FORBIDDEN
            )

        from trainers.models import Trainer
        try:
            trainer = Trainer.objects.get(user=request.user)
            wallet = TrainerWallet.objects.get(trainer=trainer)
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

        serializer = self.serializer_class(data=request.data, context={"request": request, "trainer": trainer, "wallet": wallet})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: TrainerWithdrawRequestSerializer(many=True)},
        summary='لیست درخواست‌های برداشت مربی',
        description='نمایش لیست درخواست‌های برداشت مربی جاری'
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
            withdraw_requests = TrainerWithdrawRequest.objects.filter(trainer=trainer)
            serializer = self.serializer_class(withdraw_requests, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Trainer.DoesNotExist:
            return Response(
                {'error': 'مربی‌گری برای شما یافت نشد'},
                status=status.HTTP_404_NOT_FOUND
            )
