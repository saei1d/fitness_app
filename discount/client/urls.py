from rest_framework.routers import DefaultRouter
from .discount import DiscountCodeViewSet, DiscountUsageViewSet
from .package_discount import PackageDiscountViewSet

router = DefaultRouter()
router.register(r'discount-codes', DiscountCodeViewSet, basename='discount-code')
router.register(r'discount-usages', DiscountUsageViewSet, basename='discount-usage')
router.register(r'package-discounts', PackageDiscountViewSet, basename='package-discount')

urlpatterns = router.urls
