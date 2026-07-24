from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import Trainer, TrainerGroupPackage, TrainerPackage, TrainerReview
from .serializers import (
    TrainerSerializer,
    TrainerDetailSerializer,
    TrainerGroupPackageSerializer,
    TrainerPackageSerializer,
    TrainerReviewSerializer,
    TrainerReviewCreateSerializer,
)


class IsAdminOrReadOnly(permissions.BasePermission):
    """فقط ادمین می‌تواند ایجاد/ویرایش کند، بقیه فقط خواندن"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated and request.user.is_staff


class TrainerViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت مربی‌ها"""
    queryset = Trainer.objects.filter(is_active=True).prefetch_related('active_gyms')
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'phone', 'bio']
    ordering_fields = ['name', 'average_rating', 'reviews_count', 'created_at']
    filterset_fields = ['active_gyms', 'specializations']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TrainerDetailSerializer
        return TrainerSerializer
    
    @extend_schema(
        summary='لیست مربی‌ها',
        description='نمایش لیست تمام مربی‌های فعال'
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='جزئیات مربی',
        description='نمایش جزئیات کامل یک مربی به همراه نظرات'
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary='ایجاد مربی جدید',
        description='ایجاد مربی جدید (فقط ادمین)'
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        summary='ویرایش مربی',
        description='ویرایش اطلاعات مربی (فقط ادمین)'
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @extend_schema(
        summary='حذف مربی',
        description='حذف مربی (فقط ادمین)'
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class TrainerGroupPackageViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت گروه پکیج‌های مربی"""
    queryset = TrainerGroupPackage.objects.all().select_related('trainer')
    serializer_class = TrainerGroupPackageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['title', 'trainer__name']
    filterset_fields = ['trainer']
    
    @extend_schema(tags=['Trainer Package'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TrainerPackageViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت پکیج‌های مربی"""
    queryset = TrainerPackage.objects.all().select_related(
        'group_package__trainer'
    )
    serializer_class = TrainerPackageSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'group_package__title', 'group_package__trainer__name']
    ordering_fields = ['price', 'duration', 'sessions', 'order_homepage']
    filterset_fields = ['group_package', 'gender']
    
    @extend_schema(tags=['Trainer Package'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TrainerReviewViewSet(viewsets.ModelViewSet):
    """ViewSet برای مدیریت نظرات مربی"""
    queryset = TrainerReview.objects.filter(
        deleted=False,
        blocked=False
    ).select_related('user', 'trainer', 'reply_to')
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    filterset_fields = ['trainer', 'rating']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TrainerReviewCreateSerializer
        return TrainerReviewSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # فقط نظرات اصلی (نه پاسخ‌ها)
        if self.action == 'list':
            queryset = queryset.filter(reply_to__isnull=True)
        
        return queryset
    
    @extend_schema(tags=['Trainer Review'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(tags=['Trainer Review'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(tags=['Trainer Review'])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(tags=['Trainer Review'])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @extend_schema(tags=['Trainer Review'])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """گزارش نظر توسط مربی"""
        review = self.get_object()
        user = request.user
        
        # بررسی اینکه کاربر مربی است
        if not hasattr(user, 'trainer_profile') or user.trainer_profile != review.trainer:
            return Response(
                {'detail': 'فقط مربی مربوطه می‌تواند گزارش دهد.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        review.is_reported = True
        review.save(update_fields=['is_reported'])
        return Response({'detail': 'نظر با موفقیت گزارش شد.'})
