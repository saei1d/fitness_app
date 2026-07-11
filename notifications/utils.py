import jdatetime
from django.db import models as db_models


def format_price(amount):
    """Format price by removing last two zeros and adding Toman label."""
    if amount is None:
        return '0 تومان'
    try:
        # Convert to integer and divide by 100 to remove last two zeros
        price = int(amount) // 100
        return f"{price:,} تومان"
    except Exception:
        return f"{amount} تومان"


def to_jalali(date):
    """Convert Gregorian datetime to Jalali string."""
    if date is None:
        return None
    try:
        jd = jdatetime.datetime.fromgregorian(datetime=date)
        return jd.strftime('%Y/%m/%d %H:%M')
    except Exception:
        return date.strftime('%Y-%m-%d %H:%M')


def get_all_admins():
    """Return QS of all users with role='admin' or is_superuser=True."""
    from accounts.models import User
    return User.objects.filter(
        db_models.Q(role='admin') | db_models.Q(is_superuser=True)
    )


def bulk_notify(recipients, notification_type, title, message, data=None):
    """
    Create Notification rows for an iterable of User instances in one query.
    Silently skips if recipients is empty.
    """
    from notifications.models import Notification
    notifications = [
        Notification(
            recipient=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
        )
        for user in recipients
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
