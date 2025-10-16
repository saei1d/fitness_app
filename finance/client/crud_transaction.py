from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from finance.models import Transaction, Wallet
from finance.serializers import TransactionSerializer


class IsAdminOrOwnerReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # همه لاگین باشند
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj: Transaction):
        user = request.user
        role = getattr(user, 'role', None)
        if role == 'admin':
            return True
        if role == 'owner':
            # فقط مشاهده برای مالک کیف پول خودش
            if request.method in permissions.SAFE_METHODS:
                if obj.wallet and obj.wallet.owner_id == user.id:
                    return True
        return False


class TransactionListCreateView(ListCreateAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAdminOrOwnerReadOnly]

    def get_queryset(self):
        user = self.request.user
        role = getattr(user, 'role', None)
        if role == 'admin':
            return Transaction.objects.select_related('wallet__owner', 'admin_wallet', 'purchase').all().order_by('-id')
        if role == 'owner':
            try:
                wallet = Wallet.objects.get(owner=user)
            except Wallet.DoesNotExist:
                return Transaction.objects.none()
            return Transaction.objects.filter(wallet=wallet).select_related('wallet__owner', 'admin_wallet', 'purchase').order_by('-id')
        return Transaction.objects.none()

    def perform_create(self, serializer):
        # فقط ادمین اجازه ایجاد/ویرایش/حذف دارد
        user = self.request.user
        if getattr(user, 'role', None) != 'admin':
            raise permissions.PermissionDenied("Only admin can create transactions")
        serializer.save()


class TransactionDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = TransactionSerializer
    permission_classes = [IsAdminOrOwnerReadOnly]
    lookup_field = 'pk'

    def get_queryset(self):
        # برای object-level permission نیاز به queryset پایه داریم
        return Transaction.objects.select_related('wallet__owner', 'admin_wallet', 'purchase').all()

    def perform_update(self, serializer):
        user = self.request.user
        if getattr(user, 'role', None) != 'admin':
            raise permissions.PermissionDenied("Only admin can update transactions")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if getattr(user, 'role', None) != 'admin':
            raise permissions.PermissionDenied("Only admin can delete transactions")
        instance.delete()


