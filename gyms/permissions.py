from rest_framework import permissions


class IsGymOperator(permissions.BasePermission):
    """دسترسی فقط برای متصدی‌های باشگاه"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'role', None) == 'operator'
        )
    
    def has_object_permission(self, request, view, obj):
        """چک کردن اینکه آیا متصدی به این باشگاه اختصاص داده شده است"""
        from .models import GymOperator
        
        if hasattr(obj, 'gym'):
            gym = obj.gym
        elif hasattr(obj, 'package'):
            gym = obj.package.gym
        elif hasattr(obj, 'group_package'):
            gym = obj.group_package.gym
        else:
            return False
        
        return GymOperator.objects.filter(
            gym=gym,
            operator=request.user,
            is_active=True
        ).exists()


class IsGymOperatorOrOwner(permissions.BasePermission):
    """دسترسی برای متصدی یا owner باشگاه"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            getattr(request.user, 'role', None) in ['operator', 'owner']
        )
    
    def has_object_permission(self, request, view, obj):
        user_role = getattr(request.user, 'role', None)
        
        if user_role == 'owner':
            # owner می‌تواند به باشگاه خودش دسترسی داشته باشد
            if hasattr(obj, 'gym'):
                return obj.gym.owner == request.user
            elif hasattr(obj, 'package'):
                return obj.package.gym.owner == request.user
            elif hasattr(obj, 'group_package'):
                return obj.group_package.gym.owner == request.user
            return False
        
        elif user_role == 'operator':
            # operator باید به باشگاه اختصاص داده شده باشد
            from .models import GymOperator
            
            if hasattr(obj, 'gym'):
                gym = obj.gym
            elif hasattr(obj, 'package'):
                gym = obj.package.gym
            elif hasattr(obj, 'group_package'):
                gym = obj.group_package.gym
            else:
                return False
            
            return GymOperator.objects.filter(
                gym=gym,
                operator=request.user,
                is_active=True
            ).exists()
        
        return False
