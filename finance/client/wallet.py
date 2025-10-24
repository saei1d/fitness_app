from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from finance.models import Wallet
from finance.serializers import WalletSerializer


class IsOwnerOrAdmin(permissions.BasePermission):
    """دسترسی owner به کیف پول خودش و admin به همه کیف پول‌ها"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # admin به همه دسترسی دارد
        if request.user.is_staff:
            return True
        
        # owner فقط به کیف پول خودش دسترسی دارد
        if request.user.role == 'owner':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # admin به همه دسترسی دارد
        if request.user.is_staff:
            return True
        
        # owner فقط به کیف پول خودش دسترسی دارد
        if request.user.role == 'owner':
            return obj.owner == request.user
        
        return False


@extend_schema(
    tags=['Wallet'],
    summary='نمایش جزئیات کیف پول',
    description='نمایش جزئیات کیف پول برای کاربران با رول owner'
)
class WalletDetailView(APIView):
    permission_classes = [IsOwnerOrAdmin]
    
    def get(self, request, pk):
        try:
            # اگر کاربر admin است، می‌تواند هر کیف پولی را ببیند
            if request.user.is_staff:
                wallet = Wallet.objects.get(pk=pk)
            # اگر کاربر owner است، فقط کیف پول خودش را می‌تواند ببیند
            elif request.user.role == 'owner':
                wallet = Wallet.objects.get(pk=pk, owner=request.user)
            else:
                return Response(
                    {'error': 'شما دسترسی لازم برای مشاهده این کیف پول را ندارید'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = WalletSerializer(wallet)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Wallet.DoesNotExist:
            return Response(
                {'error': 'کیف پول مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت اطلاعات کیف پول: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Wallet'],
    summary='لیست کیف پول‌های کاربر',
    description='نمایش کیف پول کاربر جاری (برای owner) یا همه کیف پول‌ها (برای admin)'
)
class WalletListView(APIView):
    permission_classes = [IsOwnerOrAdmin]
    
    def get(self, request):
        try:
            if request.user.is_staff:
                # admin می‌تواند همه کیف پول‌ها را ببیند
                wallets = Wallet.objects.all()
            elif request.user.role == 'owner':
                # owner فقط کیف پول خودش را می‌بیند
                wallets = Wallet.objects.filter(owner=request.user)
            else:
                return Response(
                    {'error': 'شما دسترسی لازم برای مشاهده کیف پول‌ها را ندارید'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = WalletSerializer(wallets, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت لیست کیف پول‌ها: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )