# interactions/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg, Count
from .models import Review

@receiver([post_save, post_delete], sender=Review)
def update_gym_rating(sender, instance, **kwargs):
    gym = instance.gym

    # فقط کامنت‌های اصلی (نه ریپلای‌ها) و نه بن‌شده‌ها
    reviews = Review.objects.filter(
        gym=gym,
        reply_to__isnull=True,
        blocked=False
    )

    data = reviews.aggregate(
        avg_rating=Avg('rating'),
        total_comments=Count('id')
    )

    gym.average_rating = data['avg_rating'] or 0
    gym.comments = data['total_comments']
    gym.save(update_fields=['average_rating', 'comments'])
