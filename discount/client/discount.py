from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db import models
from ..models import DiscountCode, DiscountUsage
from ..serializers import DiscountCodeSerializer, DiscountUsageSerializer


class IsAdminOrOwnerPermission(permissions.BasePermission):
    """دسترسی ادمین به همه کدها، owner فقط به باشگاه خودش"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # ادمین به همه دسترسی دارد
        if request.user.is_staff:
            return True
        
        # owner فقط به باشگاه خودش دسترسی دارد
        if request.user.role == 'owner':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # ادمین به همه دسترسی دارد
        if request.user.is_staff:
            return True
        
        # owner فقط به کدهای باشگاه خودش دسترسی دارد
        if request.user.role == 'owner':
            if obj.club and obj.club.owner == request.user:
                return True
        
        return False


@extend_schema(tags=['Discount Code'])
class DiscountCodeViewSet(viewsets.ModelViewSet):
    serializer_class = DiscountCodeSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwnerPermission]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            # ادمین همه کدها را می‌بیند
            return DiscountCode.objects.all().select_related('club', 'club__owner')
        elif user.role == 'owner':
            # owner فقط کدهای باشگاه خودش را می‌بیند
            return DiscountCode.objects.filter(
                club__owner=user
            ).select_related('club', 'club__owner')
        
        return DiscountCode.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        
        # اگر owner است، فقط برای باشگاه خودش کد بسازد
        if user.role == 'owner' and not user.is_staff:
            # بررسی اینکه باشگاه انتخاب شده متعلق به این owner است
            club = serializer.validated_data.get('club')
            if club and club.owner != user:
                from rest_framework import serializers
                raise serializers.ValidationError("شما فقط می‌توانید برای باشگاه خودتان کد تخفیف بسازید.")
        
        serializer.save()


@extend_schema(tags=['Discount Usage'])
class DiscountUsageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DiscountUsageSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrOwnerPermission]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_staff:
            # ادمین همه استفاده‌ها را می‌بیند
            return DiscountUsage.objects.all().select_related('discount', 'user', 'discount__club')
        elif user.role == 'owner':
            # owner فقط استفاده‌های کدهای باشگاه خودش را می‌بیند
            return DiscountUsage.objects.filter(
                discount__club__owner=user
            ).select_related('discount', 'user', 'discount__club')
        
        return DiscountUsage.objects.none()
