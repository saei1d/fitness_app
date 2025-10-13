# reviews/views.py
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from ..models import Review
from ..serializers import ReviewSerializer


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    """اجازه ویرایش فقط به نویسنده‌ی نظر"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


@extend_schema(tags=['Review'])
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().select_related('user', 'gym', 'reply_to')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsReviewOwnerOrReadOnly]

    def get_queryset(self):
        """نمایش فقط نظرات سالم و بدون بن"""
        return Review.objects.filter(
            blocked=False,
            user__is_banned_from_reviews=False
        ).select_related('user', 'gym', 'reply_to')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """صاحب باشگاه گزارش می‌دهد"""
        review = self.get_object()
        user = request.user

        if user.role != 'owner':
            return Response({'detail': 'فقط صاحبان باشگاه می‌توانند گزارش دهند.'},
                            status=status.HTTP_403_FORBIDDEN)

        if review.gym.owner != user:
            return Response({'detail': 'شما نمی‌توانید این نظر را گزارش دهید.'},
                            status=status.HTTP_403_FORBIDDEN)

        review.is_reported = True
        review.save(update_fields=['is_reported'])
        return Response({'detail': 'نظر با موفقیت گزارش شد.'})
