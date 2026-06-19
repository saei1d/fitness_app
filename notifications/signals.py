import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.utils import bulk_notify, get_all_admins

logger = logging.getLogger(__name__)


@receiver(post_save, sender='finance.Purchase', dispatch_uid='notifications.purchase_handler')
def on_purchase_post_save(sender, instance, created, **kwargs):
    _handle_payment_status(instance, created)
    _handle_verification_status(instance, created)


def _handle_payment_status(instance, created):
    """Handle payment_status → 'paid' transition."""
    if created:
        return
    if instance.payment_status != 'paid':
        return

    # Deduplication: skip if a 'purchase' notification for this purchase already exists.
    # Since post_save fires after the save, the DB already holds the new value, so we
    # cannot compare old vs new via a DB read.  Instead we guard by checking whether
    # a notification row for this purchase was already created.
    from notifications.models import Notification
    if Notification.objects.filter(
        notification_type=Notification.NotificationType.PURCHASE,
        data__purchase_id=instance.pk,
    ).exists():
        return

    # Resolve owner via purchase.package.group_package.gym.owner
    owner = None
    gym = None
    try:
        gym = instance.package.group_package.gym
        owner = gym.owner
    except Exception:
        # Incomplete chain — fall back to admin-only notification (Requirement 2.4)
        pass

    buyer = instance.user
    package = instance.package

    if gym is not None:
        title = f"خرید جدید در {gym.name} توسط {buyer.full_name or buyer.phone}"
    else:
        title = f"خرید جدید توسط {buyer.full_name or buyer.phone}"

    message = f"پکیج: {package.title} | مبلغ: {instance.final_amount}"
    data = {"purchase_id": instance.pk, "package_id": package.pk}

    if owner is not None:
        bulk_notify(
            [owner],
            Notification.NotificationType.PURCHASE,
            title,
            message,
            data,
        )

    admins = get_all_admins()
    bulk_notify(
        admins,
        Notification.NotificationType.PURCHASE,
        title,
        message,
        data,
    )


def _handle_verification_status(instance, created):
    """Handle verification_status → 'verified' transition."""
    if created:
        return
    if instance.verification_status != 'verified':
        return

    # Deduplication: skip if a plan_activated notification for this purchase already exists
    from notifications.models import Notification
    if Notification.objects.filter(
        notification_type=Notification.NotificationType.PLAN_ACTIVATED,
        data__purchase_id=instance.pk,
    ).exists():
        return

    buyer = instance.user
    package = instance.package

    # Resolve expire_date
    expire = 'نامشخص'
    if instance.expire_date:
        try:
            expire = instance.expire_date.strftime('%Y-%m-%d')
        except Exception:
            pass

    title = f"پلن شما فعال شد: {package.title}"
    message = f"پلن '{package.title}' شما فعال شد. تاریخ انقضا: {expire}"
    data = {"purchase_id": instance.pk}

    bulk_notify([buyer], Notification.NotificationType.PLAN_ACTIVATED, title, message, data)

    # Resolve owner
    owner = None
    try:
        owner = instance.package.group_package.gym.owner
    except Exception:
        pass

    if owner is not None:
        bulk_notify([owner], Notification.NotificationType.PLAN_ACTIVATED, title, message, data)


# ---------------------------------------------------------------------------
# Task 3.5 — WithdrawRequest handler
# ---------------------------------------------------------------------------

@receiver(post_save, sender='finance.WithdrawRequest', dispatch_uid='notifications.withdraw_handler')
def on_withdraw_request_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    from notifications.models import Notification

    admins = get_all_admins()
    if not admins.exists():
        logger.warning(
            "No admin users found for withdraw_request notification "
            "(withdraw_request_id=%s)", instance.pk
        )

    owner = instance.user
    title = f"درخواست برداشت از {owner.full_name or owner.phone}"
    message = f"مبلغ درخواست: {instance.amount} تومان"
    data = {"withdraw_request_id": instance.pk}

    bulk_notify(admins, Notification.NotificationType.WITHDRAW_REQUEST, title, message, data)


# ---------------------------------------------------------------------------
# Task 3.6 — TicketMessage handler
# ---------------------------------------------------------------------------

@receiver(post_save, sender='ticket.TicketMessage', dispatch_uid='notifications.ticket_message_handler')
def on_ticket_message_post_save(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        from notifications.models import Notification

        ticket_message = instance
        author = ticket_message.author
        ticket = ticket_message.ticket

        title = f"پیام جدید در تیکت: {ticket.subject}"
        message = f"از: {author.full_name or author.phone}"
        data = {"ticket_id": ticket.pk, "ticket_message_id": ticket_message.pk}

        if getattr(author, 'role', None) == 'admin' or author.is_superuser:
            # Admin replied → notify the ticket creator (customer)
            bulk_notify(
                [ticket.creator],
                Notification.NotificationType.TICKET_REPLY,
                title,
                message,
                data,
            )
        else:
            # Customer/Owner messaged → notify all admins
            admins = get_all_admins()
            bulk_notify(
                admins,
                Notification.NotificationType.TICKET_REPLY,
                title,
                message,
                data,
            )
    except Exception as e:
        logger.error(
            "Failed to create ticket_reply notification for ticket_message_id=%s: %s",
            instance.pk, e,
        )
