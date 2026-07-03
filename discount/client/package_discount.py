from rest_framework import viewsets, permissions
from drf_spectacular.utils import extend_schema, extend_schema_view
from ..models import PackageDiscount
from ..serializers import PackageDiscountSerializer


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

        # owner فقط به تخفیف‌های پکیج‌های باشگاه خودش دسترسی دارد
        if request.user.role == 'owner':
            if obj.package.group_package.gym.owner == request.user:
                return True

        return False


@extend_schema_view(
    list=extend_schema(
        summary="لیست تخفیف‌های پکیج",
        description="نمایش تخفیف‌های پکیج. ادمین‌ها همه تخفیف‌ها را می‌بینند، مالکان فقط تخفیف‌های پکیج‌های باشگاه خودشان.",
        tags=['Package Discount']
    ),
    create=extend_schema(
        summary="ایجاد تخفیف پکیج جدید",
        description="""
        ایجاد تخفیف پکیج جدید:
        - ادمین‌ها (is_staff=True): می‌توانند هر نوع تخفیفی بسازند (source_type=admin یا club)
        - مالکان (role=owner): فقط می‌توانند برای پکیج‌های باشگاه خودشان تخفیف بسازند (source_type=club)
        
        قوانین:
        - تخفیف به صورت خودکار برای همه کاربران اعمال می‌شود (بدون نیاز به کد)
        - مالکان فقط می‌توانند از source_type=club استفاده کنند
        """,
        tags=['Package Discount']
    ),
    retrieve=extend_schema(
        summary="جزئیات تخفیف پکیج",
        description="نمایش جزئیات یک تخفیف پکیج خاص",
        tags=['Package Discount']
    ),
    update=extend_schema(
        summary="ویرایش کامل تخفیف پکیج",
        description="""
        ویرایش کامل تخفیف پکیج:
        - ادمین‌ها: می‌توانند هر تخفیفی را ویرایش کنند
        - مالکان: فقط تخفیف‌های پکیج‌های باشگاه خودشان را می‌توانند ویرایش کنند
        """,
        tags=['Package Discount']
    ),
    partial_update=extend_schema(
        summary="ویرایش جزئی تخفیف پکیج",
        description="""
        ویرایش جزئی تخفیف پکیج:
        - ادمین‌ها: می‌توانند هر تخفیفی را ویرایش کنند
        - مالکان: فقط تخفیف‌های پکیج‌های باشگاه خودشان را می‌توانند ویرایش کنند
        """,
        tags=['Package Discount']
    ),
    destroy=extend_schema(
        summary="حذف تخفیف پکیج",
        description="""
        حذف تخفیف پکیج:
        - ادمین‌ها: می‌توانند هر تخفیفی را حذف کنند
        - مالکان: فقط تخفیف‌های پکیج‌های باشگاه خودشان را می‌توانند حذف کنند
        """,
        tags=['Package Discount']
    )
)
class PackageDiscountViewSet(viewsets.ModelViewSet):
    serializer_class = PackageDiscountSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwnerPermission]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return PackageDiscount.objects.all().select_related(
                'package', 'package__group_package', 'package__group_package__gym', 'package__group_package__gym__owner'
            )
        elif user.role == 'owner':
            return PackageDiscount.objects.filter(
                package__group_package__gym__owner=user
            ).select_related(
                'package', 'package__group_package', 'package__group_package__gym', 'package__group_package__gym__owner'
            )

        return PackageDiscount.objects.none()

    def perform_create(self, serializer):
        """قواعد ساخت: owner فقط برای پکیج‌های باشگاه خودش و با source_type=club، staff هر نوعی"""
        serializer.save()

    def perform_update(self, serializer):
        """قواعد ویرایش مشابه ساخت اعمال می‌شود"""
        serializer.save()
