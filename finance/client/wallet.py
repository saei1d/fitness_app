from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from accounts.permissions import is_platform_admin, operator_covers_owner, operator_owner_ids
from finance.models import Wallet, TrainerWallet
from finance.serializers import WalletSerializer, TrainerWalletSerializer


class IsOwnerOrAdmin(permissions.BasePermission):
    """دسترسی owner و trainer به کیف پول خودشان و admin به همه کیف پول‌ها"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # admin به همه دسترسی دارد
        if is_platform_admin(request.user):
            return True

        # owner فقط به کیف پول خودش دسترسی دارد
        if request.user.role == 'owner':
            return True

        # trainer فقط به کیف پول خودش دسترسی دارد
        if request.user.role == 'trainer':
            return True

        # متصدی فقط کیف پول باشگاه خودش را می‌بیند، نه همه کیف پول‌ها
        if request.user.role == 'operator':
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # admin به همه دسترسی دارد
        if is_platform_admin(request.user):
            return True

        # owner فقط به کیف پول خودش دسترسی دارد
        if request.user.role == 'owner':
            return obj.owner == request.user

        # trainer فقط به کیف پول خودش دسترسی دارد
        if request.user.role == 'trainer':
            from trainers.models import Trainer
            try:
                trainer = Trainer.objects.get(user=request.user)
                return obj.trainer == trainer
            except Trainer.DoesNotExist:
                return False

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
            if is_platform_admin(request.user):
                wallet = Wallet.objects.get(pk=pk)
            # اگر کاربر owner است، فقط کیف پول خودش را می‌تواند ببیند
            elif request.user.role == 'owner':
                wallet = Wallet.objects.get(pk=pk, owner=request.user)
            elif request.user.role == 'operator' and operator_covers_owner(request.user, Wallet.objects.filter(pk=pk).values_list('owner_id', flat=True).first()):
                wallet = Wallet.objects.get(pk=pk)
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
    summary='کیف پول کاربر',
    description='نمایش کیف پول کاربر جاری (برای owner) یا همه کیف پول‌ها (برای admin)'
)
class WalletListView(APIView):
    permission_classes = [IsOwnerOrAdmin]

    def get(self, request):
        try:
            if is_platform_admin(request.user):
                # admin می‌تواند همه کیف پول‌ها را ببیند
                wallets = Wallet.objects.all()
                serializer = WalletSerializer(wallets, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            if request.user.role == 'operator':
                wallets = Wallet.objects.filter(owner_id__in=operator_owner_ids(request.user))
                serializer = WalletSerializer(wallets, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            elif request.user.role == 'owner':
                # owner فقط کیف پول خودش را می‌بیند (به صورت آبجکت واحد)
                wallet = Wallet.objects.filter(owner=request.user).first()
                if not wallet:
                    return Response(
                        {'error': 'کیف پولی برای شما یافت نشد'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                serializer = WalletSerializer(wallet)
                return Response(serializer.data, status=status.HTTP_200_OK)
            elif request.user.role == 'trainer':
                # trainer فقط کیف پول خودش را می‌بیند
                from trainers.models import Trainer
                try:
                    trainer = Trainer.objects.get(user=request.user)
                    wallet = TrainerWallet.objects.filter(trainer=trainer).first()
                    if not wallet:
                        return Response(
                            {'error': 'کیف پولی برای شما یافت نشد'},
                            status=status.HTTP_404_NOT_FOUND
                        )
                    serializer = TrainerWalletSerializer(wallet)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                except Trainer.DoesNotExist:
                    return Response(
                        {'error': 'مربی‌گری برای شما یافت نشد'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                return Response(
                    {'error': 'شما دسترسی لازم برای مشاهده کیف پول را ندارید'},
                    status=status.HTTP_403_FORBIDDEN
                )

        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت اطلاعات کیف پول: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(
    tags=['Wallet'],
    summary='کیف پول مربی',
    description='نمایش کیف پول مربی جاری'
)
class TrainerWalletListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            if request.user.role != 'trainer':
                return Response(
                    {'error': 'این endpoint فقط برای مربیان است'},
                    status=status.HTTP_403_FORBIDDEN
                )

            from trainers.models import Trainer
            try:
                trainer = Trainer.objects.get(user=request.user)
                wallet = TrainerWallet.objects.filter(trainer=trainer).first()
                if not wallet:
                    return Response(
                        {'error': 'کیف پولی برای شما یافت نشد'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                serializer = TrainerWalletSerializer(wallet)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Trainer.DoesNotExist:
                return Response(
                    {'error': 'مربی‌گری برای شما یافت نشد'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت اطلاعات کیف پول: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )