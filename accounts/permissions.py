from rest_framework.permissions import BasePermission

# این نقش‌ها حتی اگر پرچم کارمند جنگو روشن باشد، ادمین پلتفرم نیستند.
# متصدی و مالک در محیط واقعی با همین پرچم ساخته شده‌اند و نباید به کیف پول بقیه برسند.
GYM_SIDE_ROLES = frozenset({"operator", "owner", "trainer"})


def is_platform_admin(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    role = getattr(user, "role", None)
    if role == "admin":
        return True
    if not getattr(user, "is_staff", False):
        return False
    if role in GYM_SIDE_ROLES:
        return False
    return True


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_platform_admin(getattr(request, "user", None))


def operator_owner_ids(user):
    if getattr(user, "role", None) != "operator":
        return []
    from gyms.models import GymOperator

    return GymOperator.objects.filter(
        operator=user,
        is_active=True,
    ).values_list("gym__owner_id", flat=True)


def operator_covers_owner(user, owner_id) -> bool:
    if getattr(user, "role", None) != "operator" or not owner_id:
        return False
    from gyms.models import GymOperator

    return GymOperator.objects.filter(
        operator=user,
        is_active=True,
        gym__owner_id=owner_id,
    ).exists()
