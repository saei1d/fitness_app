from django.urls import path
from rest_framework.routers import DefaultRouter
from .discount import DiscountCodeViewSet, DiscountUsageViewSet, CheckDiscountCodeView
from .package_discount import PackageDiscountViewSet

router = DefaultRouter()
router.register(r'discount-codes', DiscountCodeViewSet, basename='discount-code')
router.register(r'discount-usages', DiscountUsageViewSet, basename='discount-usage')
router.register(r'package-discounts', PackageDiscountViewSet, basename='package-discount')

urlpatterns = router.urls + [
    path('check-discount-code/', CheckDiscountCodeView.as_view(), name='check-discount-code'),
]
