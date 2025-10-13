from rest_framework.routers import DefaultRouter
from .discount import DiscountCodeViewSet, DiscountUsageViewSet

router = DefaultRouter()
router.register(r'discount-codes', DiscountCodeViewSet, basename='discount-code')
router.register(r'discount-usages', DiscountUsageViewSet, basename='discount-usage')

urlpatterns = router.urls
