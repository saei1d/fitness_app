# reviews/serializers.py
from rest_framework import serializers
from .models import Review, Favorite
from gyms.models import Gym
import json, os
from django.conf import settings


class ReviewSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    gym_name = serializers.CharField(source='gym.name', read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id',
            'user',
            'user_full_name',
            'gym',
            'gym_name',
            'rating',
            'comment',
            'created_at',
            'buyer',
            'reply_to',
            'replies',
            'is_reported',
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'buyer',
            'is_reported',
            'replies'
        ]

    def get_replies(self, obj):
        """نمایش پاسخ‌های صاحب باشگاه"""
        replies = obj.replies.all()
        return ReviewSerializer(replies, many=True).data

    def validate(self, data):
        """قوانین خاص قبل از ذخیره"""
        user = self.context['request'].user
        gym = data.get('gym')
        reply_to = data.get('reply_to')

        # جلوگیری از ارسال نظر توسط کاربر بن‌شده
        if user.is_banned_from_reviews:
            raise serializers.ValidationError("شما از ثبت نظر منع شده‌اید.")

        # جلوگیری از ثبت چند نظر برای یک باشگاه
        if not reply_to:
            # بررسی خرید کاربر از باشگاه
            has_purchased = hasattr(user, "purchases") and user.purchases.filter(package__gym=gym).exists()

            # اگر کاربر خرید نداشته و قبلاً کامنت داده، جلوی تکرار را بگیر
            if not has_purchased and Review.objects.filter(user=user, gym=gym, reply_to__isnull=True).exists():
                raise serializers.ValidationError("شما قبلاً برای این باشگاه نظر داده‌اید و امکان ثبت نظر مجدد ندارید.")

        # جلوگیری از کامنت اصلی توسط owner
        if user.role == 'owner' and not reply_to:
            raise serializers.ValidationError("صاحبان باشگاه فقط می‌توانند پاسخ دهند.")

        # اگر reply ثبت می‌شود، بررسی شود که صاحب باشگاه مربوط به همان gym است
        if reply_to:
            if user.role != 'owner':
                raise serializers.ValidationError("فقط صاحب باشگاه می‌تواند پاسخ دهد.")
            if reply_to.gym.owner != user:
                raise serializers.ValidationError("شما نمی‌توانید به این نظر پاسخ دهید.")

        return data

    def validate_comment(self, value):
        """فیلتر فحش‌ها در متن کامنت"""
        # مسیر فایل
        badwords_path = os.path.join(settings.BASE_DIR, 'badwords_fa.json')

        # اگر فایل وجود ندارد، فقط ادامه بده
        if not os.path.exists(badwords_path):
            return value

        # بارگذاری کلمات
        with open(badwords_path, 'r', encoding='utf-8') as f:
            bad_words = json.load(f)

        text = value.lower().replace("‌", "").replace(" ", "")  # حذف نیم‌فاصله و فاصله

        for word in bad_words:
            w = word.strip().lower().replace("‌", "").replace(" ", "")
            if w and w in text:
                raise serializers.ValidationError("در متن شما کلمات نامناسب وجود دارد.")

        return value

    def create(self, validated_data):
        """ایجاد نظر جدید"""
        user = self.context['request'].user
        gym = validated_data['gym']

        validated_data['user'] = user

        # بررسی سابقه خرید (فرض بر اینکه از مدل دیگری مثل Purchase استفاده می‌کنی)
        has_purchased = hasattr(user, "purchases") and user.purchases.filter(package__gym=gym).exists()
        validated_data['buyer'] = has_purchased

        review = super().create(validated_data)

        # افزایش شمارنده‌ی کامنت‌های gym
        gym.comments += 1
        gym.save(update_fields=['comments'])

        return review



class FavoriteSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.id')

    class Meta:
        model = Favorite
        fields = ['id', 'user', 'gym']
        read_only_fields = ['id', 'user']