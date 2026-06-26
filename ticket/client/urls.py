from rest_framework.routers import DefaultRouter
from .ticket import TicketViewSet, TicketMessageViewSet

router = DefaultRouter()
router.register(r'support-requests', TicketViewSet, basename='support-request')
router.register(r'support-replies', TicketMessageViewSet, basename='support-reply')

urlpatterns = router.urls

