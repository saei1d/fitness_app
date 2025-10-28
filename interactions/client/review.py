# reviews/views.py
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from ..models import Review
from ..serializers import ReviewSerializer, AdminReviewSerializer


class IsReviewOwnerOrReadOnly(permissions.BasePermission):
    """اجازه ویرایش فقط به نویسنده‌ی نظر"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class IsStaffOrReadOnly(permissions.BasePermission):
    """فقط staff می‌تواند عملیات مدیریتی انجام دهد"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_staff


@extend_schema(tags=['Review'])
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all().select_related('user', 'gym', 'reply_to')
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsReviewOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action in ['blocked_reviews', 'banned_users_reviews'] and self.request.user.is_staff:
            return AdminReviewSerializer
        return ReviewSerializer

    def get_queryset(self):
        """نمایش فقط نظرات سالم و بدون بن"""
        return Review.objects.filter(
            blocked=False,
            deleted=False,
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

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def block(self, request, pk=None):
        """ادمین نظر را بلاک می‌کند"""
        review = self.get_object()
        
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات را بلاک کنند.'},
                            status=status.HTTP_403_FORBIDDEN)

        review.blocked = True
        review.save(update_fields=['blocked'])
        return Response({'detail': 'نظر با موفقیت بلاک شد.'})

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def unblock(self, request, pk=None):
        """ادمین نظر را از بلاک خارج می‌کند"""
        review = self.get_object()
        
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات را از بلاک خارج کنند.'},
                            status=status.HTTP_403_FORBIDDEN)

        review.blocked = False
        review.save(update_fields=['blocked'])
        return Response({'detail': 'نظر با موفقیت از بلاک خارج شد.'})

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def delete_review(self, request, pk=None):
        """ادمین نظر را حذف می‌کند"""
        review = self.get_object()
        
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات را حذف کنند.'},
                            status=status.HTTP_403_FORBIDDEN)

        review.deleted = True
        review.save(update_fields=['deleted'])
        return Response({'detail': 'نظر با موفقیت حذف شد.'})

    @action(detail=True, methods=['patch'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def restore_review(self, request, pk=None):
        """ادمین نظر حذف شده را بازگردانی می‌کند"""
        review = self.get_object()
        
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات را بازگردانی کنند.'},
                            status=status.HTTP_403_FORBIDDEN)

        review.deleted = False
        review.save(update_fields=['deleted'])
        return Response({'detail': 'نظر با موفقیت بازگردانی شد.'})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def blocked_reviews(self, request):
        """نمایش نظرات بلاک شده (فقط برای ادمین‌ها)"""
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات بلاک شده را ببینند.'},
                            status=status.HTTP_403_FORBIDDEN)

        blocked_reviews = Review.objects.filter(blocked=True).select_related('user', 'gym', 'reply_to')
        serializer = self.get_serializer(blocked_reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def banned_users_reviews(self, request):
        """نمایش نظرات کاربران بن‌شده (فقط برای ادمین‌ها)"""
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات کاربران بن‌شده را ببینند.'},
                            status=status.HTTP_403_FORBIDDEN)

        banned_reviews = Review.objects.filter(user__is_banned_from_reviews=True).select_related('user', 'gym', 'reply_to')
        serializer = self.get_serializer(banned_reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def deleted_reviews(self, request):
        """نمایش نظرات حذف شده (فقط برای ادمین‌ها)"""
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات حذف شده را ببینند.'},
                            status=status.HTTP_403_FORBIDDEN)

        deleted_reviews = Review.objects.filter(deleted=True).select_related('user', 'gym', 'reply_to')
        serializer = self.get_serializer(deleted_reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsStaffOrReadOnly])
    def reported_reviews(self, request):
        """نمایش نظرات گزارش شده (فقط برای ادمین‌ها)"""
        if not request.user.is_staff:
            return Response({'detail': 'فقط ادمین‌ها می‌توانند نظرات گزارش شده را ببینند.'},
                            status=status.HTTP_403_FORBIDDEN)

        reported_reviews = Review.objects.filter(is_reported=True).select_related('user', 'gym', 'reply_to')
        serializer = self.get_serializer(reported_reviews, many=True)
        return Response(serializer.data)
