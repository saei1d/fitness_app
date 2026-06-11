from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from decimal import Decimal
from django.db import transaction
from finance.models import Wallet, Transaction, Purchase,AdminWallet
from finance.serializers import *
from accounts.models import User


class IsStaffPermission(permissions.BasePermission):
    """دسترسی فقط برای staff users"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminWalletListView(APIView):
    """نمایش کیف پول ادمین"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Wallet'],
        summary='کیف پول ادمین',
        description='نمایش موجودی کیف پول ادمین'
    )
    def get(self, request):
        try:
            admin_wallet = AdminWallet.objects.get(id=1)
            serializer = AdminWalletSerializer(admin_wallet)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AdminWallet.DoesNotExist:
            # اگر کیف پول ادمین وجود نداشت، آن را ایجاد می‌کنیم
            admin_wallet = AdminWallet.objects.create(id=1, balance=0)
            serializer = AdminWalletSerializer(admin_wallet)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت کیف پول ادمین: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminWalletDetailView(APIView):
    """جزئیات و مدیریت کیف پول خاص برای admin"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Wallet'],
        summary='جزئیات کیف پول',
        description='نمایش جزئیات کیف پول خاص'
    )
    def get(self, request, pk):
        try:
            wallet = Wallet.objects.select_related('owner').get(pk=pk)
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


class AdminWalletBalanceUpdateView(APIView):
    """به‌روزرسانی موجودی کیف پول توسط admin"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Wallet'],
        summary='به‌روزرسانی موجودی کیف پول',
        description='افزایش یا کاهش موجودی کیف پول توسط admin',
        request={
            'type': 'object',
            'properties': {
                'operation': {
                    'type': 'string',
                    'enum': ['add', 'subtract', 'set'],
                    'description': 'نوع عملیات: add (افزایش), subtract (کاهش), set (تنظیم مستقیم)'
                },
                'amount': {
                    'type': 'number',
                    'description': 'مقدار'
                },
                'description': {
                    'type': 'string',
                    'description': 'توضیحات عملیات'
                }
            },
            'required': ['operation', 'amount']
        }
    )
    def post(self, request, pk):
        try:
            wallet = Wallet.objects.get(pk=pk)
            operation = request.data.get('operation')
            amount = Decimal(str(request.data.get('amount', 0)))
            description = request.data.get('description', '')
            
            if operation not in ['add', 'subtract', 'set']:
                return Response(
                    {'error': 'عملیات نامعتبر. عملیات مجاز: add, subtract, set'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if amount <= 0:
                return Response(
                    {'error': 'مقدار باید بزرگتر از صفر باشد'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            with transaction.atomic():
                old_balance = wallet.balance
                
                if operation == 'add':
                    wallet.balance += amount
                    transaction_type = 'credit'
                    transaction_description = f'افزایش موجودی توسط admin: {description}'
                elif operation == 'subtract':
                    if wallet.balance < amount:
                        return Response(
                            {'error': 'موجودی کافی نیست'}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    wallet.balance -= amount
                    transaction_type = 'debit'
                    transaction_description = f'کاهش موجودی توسط admin: {description}'
                elif operation == 'set':
                    wallet.balance = amount
                    transaction_type = 'credit' if amount > old_balance else 'debit'
                    transaction_description = f'تنظیم مستقیم موجودی توسط admin: {description}'
                
                wallet.save()
                
                # ایجاد تراکنش
                Transaction.objects.create(
                    wallet=wallet,
                    amount=abs(amount - old_balance) if operation == 'set' else amount,
                    type=transaction_type,
                    status='completed',
                    description=transaction_description,
                    payment_id=None
                )
                
                return Response({
                    'message': 'موجودی با موفقیت به‌روزرسانی شد',
                    'old_balance': float(old_balance),
                    'new_balance': float(wallet.balance),
                    'operation': operation,
                    'amount': float(amount)
                }, status=status.HTTP_200_OK)
                
        except Wallet.DoesNotExist:
            return Response(
                {'error': 'کیف پول مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در به‌روزرسانی موجودی: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminWalletTransactionsView(APIView):
    """لیست تراکنش‌های کیف پول برای admin"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Wallet'],
        summary='تراکنش‌های کیف پول',
        description='نمایش تراکنش‌های کیف پول خاص'
    )
    def get(self, request, pk):
        try:
            wallet = Wallet.objects.get(pk=pk)
            transactions = wallet.transactions.all().order_by('-created_at')
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Wallet.DoesNotExist:
            return Response(
                {'error': 'کیف پول مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت تراکنش‌ها: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminWalletSearchView(APIView):
    """جستجوی کیف پول بر اساس owner"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Wallet'],
        summary='جستجوی کیف پول',
        description='جستجوی کیف پول بر اساس شماره تلفن یا نام مالک'
    )
    def get(self, request):
        try:
            phone = request.query_params.get('phone')
            name = request.query_params.get('name')
            
            wallets = Wallet.objects.select_related('owner').all()
            
            if phone:
                wallets = wallets.filter(owner__phone__icontains=phone)
            
            if name:
                wallets = wallets.filter(owner__full_name__icontains=name)
            
            serializer = WalletSerializer(wallets, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در جستجوی کیف پول‌ها: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminPurchaseListView(APIView):
    """لیست همه purchase ها برای admin"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Purchase'],
        summary='لیست همه خریدها',
        description='نمایش همه purchase ها برای admin با امکان فیلتر و جستجو'
    )
    def get(self, request):
        try:
            purchases = Purchase.objects.select_related('user', 'package', 'verified_by').all()
            
            # فیلتر بر اساس وضعیت پرداخت
            payment_status = request.query_params.get('payment_status')
            if payment_status:
                purchases = purchases.filter(payment_status=payment_status)
            
            # فیلتر بر اساس وضعیت تایید
            verification_status = request.query_params.get('verification_status')
            if verification_status:
                purchases = purchases.filter(verification_status=verification_status)
            
            # جستجو بر اساس شماره تلفن کاربر
            phone = request.query_params.get('phone')
            if phone:
                purchases = purchases.filter(user__phone__icontains=phone)
            
            # جستجو بر اساس نام کاربر
            name = request.query_params.get('name')
            if name:
                purchases = purchases.filter(user__full_name__icontains=name)
            
            # جستجو بر اساس buyer_code
            buyer_code = request.query_params.get('buyer_code')
            if buyer_code:
                purchases = purchases.filter(buyer_code__icontains=buyer_code)
            
            # مرتب‌سازی
            ordering = request.query_params.get('ordering', '-purchase_date')
            purchases = purchases.order_by(ordering)
            
            serializer = PurchaseSerializer(purchases, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت لیست خریدها: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminPurchaseDetailView(APIView):
    """جزئیات purchase خاص برای admin"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Purchase'],
        summary='جزئیات خرید',
        description='نمایش جزئیات کامل purchase خاص'
    )
    def get(self, request, pk):
        try:
            purchase = Purchase.objects.select_related('user', 'package', 'verified_by').get(pk=pk)
            serializer = PurchaseSerializer(purchase)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Purchase.DoesNotExist:
            return Response(
                {'error': 'خرید مورد نظر یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت اطلاعات خرید: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminWalletTransactionsView(APIView):
    """تراکنش‌های کیف پول ادمین"""
    permission_classes = [IsStaffPermission]
    
    @extend_schema(
        tags=['Admin Wallet'],
        summary='تراکنش‌های کیف پول ادمین',
        description='نمایش تراکنش‌های کیف پول ادمین'
    )
    def get(self, request):
        try:
            admin_wallet = AdminWallet.objects.get(id=1)
            transactions = admin_wallet.transactions.all().order_by('-created_at')
            serializer = TransactionSerializer(transactions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except AdminWallet.DoesNotExist:
            return Response(
                {'error': 'کیف پول ادمین یافت نشد'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'خطا در دریافت تراکنش‌ها: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
