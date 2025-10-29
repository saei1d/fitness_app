from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from ..serializers import *
from django.db import transaction


@extend_schema(tags=['Admin Withdraw Request'])
class AdminWithdrawRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AdminWithdrawUpdateSerializer

    @extend_schema(
        request=AdminWithdrawUpdateSerializer,
        responses={200: AdminWithdrawUpdateSerializer, 400: dict, 404: dict},
        summary='به‌روزرسانی درخواست برداشت',
        description='به‌روزرسانی وضعیت درخواست برداشت توسط admin (approve/reject/complete)'
    )
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


class IsStaffPermission(permissions.BasePermission):
    """دسترسی فقط برای staff users"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminWithdrawRequestListView(APIView):
    """لیست همه درخواست‌های برداشت برای admin"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Withdraw Request'],
        summary='لیست همه درخواست‌های برداشت',
        description='نمایش همه درخواست‌های برداشت برای admin با امکان فیلتر'
    )
    def get(self, request):
        try:
            withdraw_requests = WithdrawRequest.objects.select_related('user', 'wallet__owner').all()
            
            # فیلتر بر اساس وضعیت
            status_filter = request.query_params.get('status')
            if status_filter:
                withdraw_requests = withdraw_requests.filter(status=status_filter)
            
            # جستجو بر اساس شماره تلفن کاربر
            phone = request.query_params.get('phone')
            if phone:
                withdraw_requests = withdraw_requests.filter(user__phone__icontains=phone)
            
            # جستجو بر اساس نام کاربر
            name = request.query_params.get('name')
            if name:
                withdraw_requests = withdraw_requests.filter(user__full_name__icontains=name)
            
            # مرتب‌سازی
            ordering = request.query_params.get('ordering', '-id')
            withdraw_requests = withdraw_requests.order_by(ordering)
            
            serializer = WithdrawRequestSerializer(withdraw_requests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت لیست درخواست‌های برداشت: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminWithdrawRequestDetailView(APIView):
    """جزئیات درخواست برداشت خاص برای admin"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Withdraw Request'],
        summary='جزئیات درخواست برداشت',
        description='نمایش جزئیات کامل درخواست برداشت خاص'
    )
    def get(self, request, pk):
        try:
            withdraw_request = WithdrawRequest.objects.select_related('user', 'wallet__owner').get(pk=pk)
            serializer = WithdrawRequestSerializer(withdraw_request)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except WithdrawRequest.DoesNotExist:
            return Response(
                {'error': 'درخواست برداشت مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت اطلاعات درخواست برداشت: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    