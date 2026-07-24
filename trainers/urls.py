from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainerViewSet, TrainerGroupPackageViewSet, TrainerPackageViewSet, TrainerReviewViewSet

router = DefaultRouter()
router.register(r'trainers', TrainerViewSet, basename='trainer')
router.register(r'trainer-group-packages', TrainerGroupPackageViewSet, basename='trainer-group-package')
router.register(r'trainer-packages', TrainerPackageViewSet, basename='trainer-package')
router.register(r'trainer-reviews', TrainerReviewViewSet, basename='trainer-review')

urlpatterns = router.urls
