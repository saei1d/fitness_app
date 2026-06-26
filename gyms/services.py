from accounts.models import User
from finance.models import Wallet


def resolve_gym_owner(owner_value):
    """
    Resolve an owner reference that may be a user id or a phone number.

    The API accepts either a numeric id or an 11-digit phone number.
    """
    if owner_value is None or owner_value == "":
        raise ValueError("owner field is required to assign an owner.")

    owner_value_str = str(owner_value).strip()
    if not owner_value_str:
        raise ValueError("owner field is required to assign an owner.")

    if owner_value_str.isdigit() and len(owner_value_str) == 11:
        try:
            return User.objects.get(phone=owner_value_str)
        except User.DoesNotExist as exc:
            raise ValueError(f"No user found with phone number: {owner_value_str}") from exc

    try:
        return User.objects.get(id=owner_value)
    except User.DoesNotExist as exc:
        raise ValueError(f"No user found with id: {owner_value}") from exc


def promote_gym_owner(user):
    """
    Ensure a gym owner has the correct role and wallet.
    """
    if user.role != "owner":
        user.role = "owner"
        user.save(update_fields=["role"])

    Wallet.objects.get_or_create(owner=user)
    return user
