import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


def send_plan_expiry_notifications():
    """
    Run daily. Creates plan_expired notifications for:
      1. Purchases expiring TODAY (expire_date__date == today)
      2. Purchases expiring in 3 DAYS (expire_date__date == today + 3)
    Deduplicates via (recipient, notification_type='plan_expired', data__purchase_id) check.
    Skips purchases with expire_date=None (Requirement 4.5).
    """
    from finance.models import Purchase
    from notifications.models import Notification
    from notifications.utils import bulk_notify

    today = timezone.now().date()

    targets = [
        (today,                      f"پلن شما امروز منقضی می‌شود"),
        (today + timedelta(days=3),  f"پلن شما ۳ روز دیگر منقضی می‌شود"),
    ]

    for target_date, title_prefix in targets:
        purchases = Purchase.objects.filter(
            expire_date__date=target_date,
            verification_status='verified',
        ).select_related('user', 'package')

        for purchase in purchases:
            already_notified = Notification.objects.filter(
                recipient=purchase.user,
                notification_type=Notification.NotificationType.PLAN_EXPIRED,
                data__purchase_id=purchase.pk,
            ).exists()

            if not already_notified:
                title = f"{title_prefix}: {purchase.package.title}"
                message = (
                    f"تاریخ انقضای پلن '{purchase.package.title}': "
                    f"{purchase.expire_date.strftime('%Y-%m-%d')}"
                )
                data = {"purchase_id": purchase.pk}
                try:
                    bulk_notify(
                        [purchase.user],
                        Notification.NotificationType.PLAN_EXPIRED,
                        title,
                        message,
                        data,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to create plan_expired notification for purchase %s: %s",
                        purchase.pk, e,
                    )
