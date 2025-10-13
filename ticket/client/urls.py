from rest_framework.routers import DefaultRouter
from .ticket import TicketViewSet, TicketMessageViewSet

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'ticket-messages', TicketMessageViewSet, basename='ticket-message')

urlpatterns = router.urls

