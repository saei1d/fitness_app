from django.db import models
from django.utils import timezone


class Review(models.Model):
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    gym = models.ForeignKey(
        'gyms.Gym',
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    is_reported = models.BooleanField(default=False)  # اگر گزارش شده
    buyer = models.BooleanField(default=False)  # اگر از این باشگاه خرید داشته
    blocked = models.BooleanField(default=False)  # اگر ادمین او را بن کرده باشد
    deleted = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )  # پاسخ صاحب باشگاه
