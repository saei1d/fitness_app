from django.db import models
from django.conf import settings


class Notification(models.Model):

    class NotificationType(models.TextChoices):
        PURCHASE          = 'purchase',         'Purchase'
        PLAN_ACTIVATED    = 'plan_activated',   'Plan Activated'
        PLAN_EXPIRED      = 'plan_expired',     'Plan Expired'
        TICKET_REPLY      = 'ticket_reply',     'Ticket Reply'
        TICKET_CREATED    = 'ticket_created',   'Ticket Created'
        WITHDRAW_REQUEST  = 'withdraw_request', 'Withdraw Request'

    recipient         = models.ForeignKey(
                            settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            related_name='notifications',
                        )
    notification_type = models.CharField(
                            max_length=30,
                            choices=NotificationType.choices,
                        )
    title             = models.CharField(max_length=255)
    message           = models.TextField(max_length=2000)
    is_read           = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)
    data              = models.JSONField(null=True, blank=True, default=None)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['notification_type']),
        ]
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.notification_type}] {self.recipient} — {self.title[:40]}"
