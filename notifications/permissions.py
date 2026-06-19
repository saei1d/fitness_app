from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Allows access only to users with role='admin' or is_superuser=True."""

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (getattr(request.user, 'role', None) == 'admin' or
             request.user.is_superuser)
        )


class IsNotificationOwner(BasePermission):
    """Object-level permission: only the notification's recipient may act on it."""

    def has_object_permission(self, request, view, obj):
        return obj.recipient_id == request.user.pk
