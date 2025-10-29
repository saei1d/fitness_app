from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from finance.models import WithdrawRequest
from finance.serializers import WithdrawRequestSerializer


@extend_schema(tags=['Withdraw Request'])
class WithdrawRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawRequestSerializer
    
    @extend_schema(
        request=WithdrawRequestSerializer,
        responses={201: WithdrawRequestSerializer},
        summary='ایجاد درخواست برداشت',
        description='ایجاد درخواست برداشت برای کاربران owner'
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        responses={200: WithdrawRequestSerializer(many=True)},
        summary='لیست درخواست‌های برداشت',
        description='نمایش لیست درخواست‌های برداشت کاربر جاری'
    )
    def get(self, request):
        withdraw_requests = WithdrawRequest.objects.filter(user=request.user)
        serializer = self.serializer_class(withdraw_requests, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


