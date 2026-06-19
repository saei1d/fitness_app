from django.db import models as db_models


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
