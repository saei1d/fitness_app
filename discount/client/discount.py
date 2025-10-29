from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db import models
from ..models import DiscountCode, DiscountUsage
from ..serializers import DiscountCodeSerializer, DiscountUsageSerializer


class IsAdminOrOwnerPermission(permissions.BasePermission):


    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # خواندن برای همه کاربران لاگین‌شده مجاز است
        if request.method in permissions.SAFE_METHODS:
            return True

        # عملیات نوشتن فقط برای staff یا owner
        if request.user.is_staff:
            return True
        if getattr(request.user, 'role', None) == 'owner':
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # ادمین به همه دسترسی دارد
        if request.user.is_staff:
            return True

        # owner فقط به کدهای باشگاه خودش دسترسی دارد
        if request.user.role == 'owner':
            # کدهای admin بدون باشگاه برای owner قابل دسترسی/ویرایش نیست
            if obj.source_type == 'admin':
                return False
            if obj.club and obj.club.owner == request.user:
                return True

        return False


@extend_schema_view(
    list=extend_schema(
        summary="لیست کدهای تخفیف",
        description="نمایش کدهای تخفیف. ادمین‌ها همه کدها را می‌بینند، مالکان فقط کدهای باشگاه خودشان.",
        tags=['Discount Code']
    ),
    create=extend_schema(
        summary="ایجاد کد تخفیف جدید",
        description="""
        ایجاد کد تخفیف جدید:
        - ادمین‌ها (is_staff=True): می‌توانند هر نوع کدی بسازند (source_type=admin یا club)
        - مالکان (role=owner): فقط می‌توانند برای باشگاه خودشان کد بسازند (source_type=club)
        
        قوانین:
        - اگر source_type='admin' باشد، club باید null باشد
        - اگر source_type='club' باشد، club باید انتخاب شود
        - کد تخفیف باید یکتا باشد
        """,
        tags=['Discount Code']
    ),
    retrieve=extend_schema(
        summary="جزئیات کد تخفیف",
        description="نمایش جزئیات یک کد تخفیف خاص",
        tags=['Discount Code']
    ),
    update=extend_schema(
        summary="ویرایش کامل کد تخفیف",
        description="""
        ویرایش کامل کد تخفیف:
        - ادمین‌ها: می‌توانند هر کدی را ویرایش کنند
        - مالکان: فقط کدهای باشگاه خودشان را می‌توانند ویرایش کنند
        """,
        tags=['Discount Code']
    ),
    partial_update=extend_schema(
        summary="ویرایش جزئی کد تخفیف",
        description="""
        ویرایش جزئی کد تخفیف:
        - ادمین‌ها: می‌توانند هر کدی را ویرایش کنند
        - مالکان: فقط کدهای باشگاه خودشان را می‌توانند ویرایش کنند
        """,
        tags=['Discount Code']
    ),
    destroy=extend_schema(
        summary="حذف کد تخفیف",
        description="""
        حذف کد تخفیف:
        - ادمین‌ها: می‌توانند هر کدی را حذف کنند
        - مالکان: فقط کدهای باشگاه خودشان را می‌توانند حذف کنند
        """,
        tags=['Discount Code']
    )
)
class DiscountCodeViewSet(viewsets.ModelViewSet):
    serializer_class = DiscountCodeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwnerPermission]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return DiscountCode.objects.all().select_related('club', 'club__owner')
        elif user.role == 'owner':
            return DiscountCode.objects.filter(
                club__owner=user
            ).select_related('club', 'club__owner')

        return DiscountCode.objects.none()

    def perform_create(self, serializer):
        """قواعد ساخت: owner فقط برای باشگاه خودش و با source_type=club، staff هر نوعی"""
        serializer.save()

    def perform_update(self, serializer):
        """قواعد ویرایش مشابه ساخت اعمال می‌شود"""
        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="لیست استفاده‌های کد تخفیف",
        description="نمایش استفاده‌های کدهای تخفیف. ادمین‌ها همه استفاده‌ها را می‌بینند، مالکان فقط استفاده‌های کدهای باشگاه خودشان.",
        tags=['Discount Usage']
    ),
    retrieve=extend_schema(
        summary="جزئیات استفاده از کد تخفیف",
        description="نمایش جزئیات یک استفاده خاص از کد تخفیف",
        tags=['Discount Usage']
    )
)
class DiscountUsageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DiscountUsageSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwnerPermission]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            # ادمین همه استفاده‌ها را می‌بیند
            return DiscountUsage.objects.all().select_related('discount', 'user', 'discount__club')
        elif user.role == 'owner':
            # owner فقط استفاده‌های کدهای باشگاه خودش را می‌بیند
            return DiscountUsage.objects.filter(
                discount__club__owner=user
            ).select_related('discount', 'user', 'discount__club')

        return DiscountUsage.objects.none()
