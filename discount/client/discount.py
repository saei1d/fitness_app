from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample, OpenApiResponse
from django.db import models
from django.db.models import Q
from django.utils import timezone
from ..models import DiscountCode, DiscountUsage
from ..serializers import DiscountCodeSerializer, DiscountUsageSerializer
from drf_spectacular.utils import extend_schema_view
from decimal import Decimal
from packages.models import Package


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

        discount = getattr(obj, 'discount', obj)

        # owner فقط به کدهای باشگاه خودش دسترسی دارد
        if request.user.role == 'owner':
            # کدهای admin بدون باشگاه برای owner قابل دسترسی/ویرایش نیست
            if discount.source_type == 'admin':
                return False
            if discount.gym and discount.gym.owner == request.user:
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
            return DiscountCode.objects.all().select_related('gym', 'gym__owner').prefetch_related('packages')
        elif user.role == 'owner':
            return DiscountCode.objects.filter(
                gym__owner=user
            ).select_related('gym', 'gym__owner').prefetch_related('packages')

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
            return DiscountUsage.objects.all().select_related('discount', 'user', 'discount__gym').prefetch_related('discount__packages')
        elif user.role == 'owner':
            # owner فقط استفاده‌های کدهای باشگاه خودش را می‌بیند
            return DiscountUsage.objects.filter(
                discount__gym__owner=user
            ).select_related('discount', 'user', 'discount__gym').prefetch_related('discount__packages')

        return DiscountUsage.objects.none()


@extend_schema(tags=['Discount Code'])
class CheckDiscountCodeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Check discount code validity and calculate discount",
        description="Check if a discount code is valid for a specific package, and calculate the total discount (including package discount if applicable). This does NOT use/consume the discount code.",
        parameters=[
            OpenApiParameter(name='code', description='Discount code to check', required=True, type=OpenApiTypes.STR),
            OpenApiParameter(name='package_id', description='Package ID to check discount against', required=True, type=OpenApiTypes.INT),
        ],
        responses={
            200: OpenApiResponse(
                description="Discount code check result",
                examples=[
                    OpenApiExample(
                        'Valid discount code',
                        value={
                            'is_valid': True,
                            'discount_code': 'SUMMER2024',
                            'discount_type': 'percent',
                            'discount_value': '10.00',
                            'code_discount_amount': '8500.00',
                            'package_discount_amount': '5000.00',
                            'total_discount': '13500.00',
                            'original_price': '100000.00',
                            'final_price': '86500.00',
                        },
                    ),
                    OpenApiExample(
                        'Invalid discount code',
                        value={
                            'is_valid': False,
                            'error': 'کد تخفیف معتبر نیست یا ظرفیت آن تمام شده است',
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Missing required parameters",
                examples=[
                    OpenApiExample(
                        'Missing required parameters',
                        value={'error': 'code and package_id are required'},
                    ),
                ],
            ),
            404: OpenApiResponse(
                description="Package not found",
                examples=[
                    OpenApiExample(
                        'Package not found',
                        value={'error': 'Package not found'},
                    ),
                ],
            ),
        },
    )
    def get(self, request):
        code = request.query_params.get('code')
        package_id = request.query_params.get('package_id')

        if not code or not package_id:
            return Response({'error': 'code and package_id are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            package = Package.objects.get(id=package_id)
        except Package.DoesNotExist:
            return Response({'error': 'Package not found'}, status=status.HTTP_404_NOT_FOUND)

        code = code.strip()
        discount = DiscountCode.objects.filter(code=code).prefetch_related('packages').first()
        if not discount:
            return Response({'error': 'کد تخفیف یافت نشد', 'is_valid': False}, status=status.HTTP_200_OK)

        if not discount.is_valid():
            return Response({'error': 'کد تخفیف معتبر نیست یا ظرفیت آن تمام شده است', 'is_valid': False}, status=status.HTTP_200_OK)

        user = request.user
        gym = package.group_package.gym

        # Check if discount applies to this gym
        if discount.gym and discount.gym_id != gym.id:
            return Response({'error': 'این کد برای باشگاه انتخاب‌شده معتبر نیست', 'is_valid': False}, status=status.HTTP_200_OK)

        # Check if discount applies to this package
        if discount.packages.exists():
            if package not in discount.packages.all():
                return Response({'error': 'این کد برای پکیج انتخاب‌شده معتبر نیست', 'is_valid': False}, status=status.HTTP_200_OK)

        if not discount.can_user_use(user):
            return Response({'error': 'شما مجاز به استفاده از این کد نیستید', 'is_valid': False}, status=status.HTTP_200_OK)

        # Now calculate discounts (package discount first, then code discount)
        total_amount = package.price
        commission_rate = Decimal(str(package.commission_rate))
        admin_commission_before_discount = total_amount * commission_rate

        # Get package discount
        package_discount_obj = package.discounts.filter(
            is_active=True,
        ).filter(
            Q(start_date__isnull=True) | Q(start_date__lte=timezone.now()),
            Q(end_date__isnull=True) | Q(end_date__gte=timezone.now()),
        ).first()

        package_discount_amount = Decimal('0')
        if package_discount_obj:
            if package_discount_obj.discount_type == 'percent':
                requested_percent = Decimal(str(package_discount_obj.value))
                if requested_percent < Decimal('1'):
                    requested_percent = requested_percent * Decimal('100')
                if package_discount_obj.source_type == 'admin':
                    max_admin_percent = (commission_rate * Decimal('100')).quantize(Decimal('1.0000'))
                    effective_percent = min(requested_percent, max_admin_percent)
                else:
                    effective_percent = requested_percent
                package_discount_amount = (total_amount * effective_percent) / Decimal('100')
            else:  # amount
                requested_amount = Decimal(str(package_discount_obj.value))
                if package_discount_obj.source_type == 'admin':
                    effective_amount = min(requested_amount, admin_commission_before_discount)
                else:
                    effective_amount = requested_amount
                package_discount_amount = effective_amount

        # Calculate code discount
        price_after_package_discount = total_amount - package_discount_amount
        code_discount_amount = Decimal('0')
        if discount.discount_type == 'percent':
            requested_percent = Decimal(str(discount.value))
            if requested_percent < Decimal('1'):
                requested_percent = requested_percent * Decimal('100')
            if discount.source_type == 'admin':
                max_admin_percent = (commission_rate * Decimal('100')).quantize(Decimal('1.0000'))
                effective_percent = min(requested_percent, max_admin_percent)
            else:
                effective_percent = requested_percent
            code_discount_amount = (price_after_package_discount * effective_percent) / Decimal('100')
        else:  # amount
            requested_amount = Decimal(str(discount.value))
            if discount.source_type == 'admin':
                effective_amount = min(requested_amount, admin_commission_before_discount)
            else:
                effective_amount = requested_amount
            code_discount_amount = effective_amount

        total_discount = package_discount_amount + code_discount_amount
        final_amount = total_amount - total_discount
        if final_amount < 0:
            final_amount = Decimal('0')

        return Response({
            'is_valid': True,
            'discount_code': discount.code,
            'discount_type': discount.discount_type,
            'discount_value': discount.value,
            'code_discount_amount': code_discount_amount,
            'package_discount_amount': package_discount_amount,
            'total_discount': total_discount,
            'original_price': total_amount,
            'final_price': final_amount,
        }, status=status.HTTP_200_OK)
