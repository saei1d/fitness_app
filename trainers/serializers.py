from rest_framework import serializers
from .models import Trainer, TrainerGroupPackage, TrainerPackage, TrainerReview
import json, os
from django.conf import settings


class TrainerSerializer(serializers.ModelSerializer):
    """Serializer برای نمایش لیست مربی‌ها"""
    active_gyms_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Trainer
        fields = [
            'id',
            'name',
            'phone',
            'image',
            'specializations',
            'teaching_experience_years',
            'certifications',
            'special_expertise',
            'active_gyms',
            'active_gyms_names',
            'active_students_count',
            'bio',
            'average_rating',
            'reviews_count',
            'order_homepage',
            'created_at',
            'is_active',
        ]
        read_only_fields = [
            'id',
            'average_rating',
            'reviews_count',
            'created_at',
        ]
    
    def get_active_gyms_names(self, obj):
        return [gym.name for gym in obj.active_gyms.all()]


class TrainerDetailSerializer(serializers.ModelSerializer):
    """Serializer برای نمایش جزئیات مربی"""
    active_gyms = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    packages = serializers.SerializerMethodField()
    
    class Meta:
        model = Trainer
        fields = [
            'id',
            'name',
            'phone',
            'image',
            'specializations',
            'teaching_experience_years',
            'certifications',
            'special_expertise',
            'active_gyms',
            'active_students_count',
            'bio',
            'average_rating',
            'reviews_count',
            'created_at',
            'updated_at',
            'is_active',
            'packages',
            'reviews',
        ]
        read_only_fields = [
            'id',
            'average_rating',
            'reviews_count',
            'created_at',
            'updated_at',
        ]
    
    def get_active_gyms(self, obj):
        from gyms.serializers import GymSerializer
        return GymSerializer(obj.active_gyms.all(), many=True).data
    
    def get_reviews(self, obj):
        reviews = obj.reviews.filter(
            deleted=False,
            blocked=False,
            reply_to__isnull=True
        )[:10]
        return TrainerReviewSerializer(reviews, many=True).data

    def get_packages(self, obj):
        packages = obj.packages.select_related('group_package').order_by(
            'group_package_id',
            'order_homepage',
            'id',
        )
        return TrainerPackageSerializer(packages, many=True, context=self.context).data


class TrainerGroupPackageSerializer(serializers.ModelSerializer):
    """Serializer برای گروه پکیج مربی"""
    
    class Meta:
        model = TrainerGroupPackage
        fields = [
            'id',
            'title',
            'description',
        ]
        read_only_fields = ['id']


class TrainerPackageSerializer(serializers.ModelSerializer):
    """Serializer برای پکیج مربی"""
    trainer_name = serializers.CharField(source='trainer.name', read_only=True)
    group_package_title = serializers.CharField(source='group_package.title', read_only=True)
    
    class Meta:
        model = TrainerPackage
        fields = [
            'id',
            'trainer',
            'trainer_name',
            'group_package',
            'group_package_title',
            'title',
            'description',
            'gender',
            'price',
            'duration',
            'commission_rate',
            'sessions',
            'order_homepage',
        ]
        read_only_fields = ['id']


class TrainerReviewSerializer(serializers.ModelSerializer):
    """Serializer برای نظرات مربی"""
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    trainer_name = serializers.CharField(source='trainer.name', read_only=True)
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainerReview
        fields = [
            'id',
            'trainer',
            'trainer_name',
            'user',
            'user_full_name',
            'rating',
            'comment',
            'created_at',
            'buyer',
            'reply_to',
            'replies',
            'is_reported',
            'blocked',
            'deleted',
        ]
        read_only_fields = [
            'id',
            'user',
            'created_at',
            'buyer',
            'is_reported',
            'replies',
            'blocked',
            'deleted',
        ]
    
    def get_replies(self, obj):
        """نمایش پاسخ‌های مربی"""
        replies = obj.replies.filter(blocked=False, deleted=False)
        return TrainerReviewSerializer(replies, many=True, context=self.context).data
    
    def validate(self, data):
        """قوانین خاص قبل از ذخیره"""
        user = self.context['request'].user
        trainer = data.get('trainer')
        reply_to = data.get('reply_to')
        
        # جلوگیری از ثبت چند نظر برای یک مربی
        if not reply_to:
            if TrainerReview.objects.filter(
                user=user,
                trainer=trainer,
                reply_to__isnull=True,
                deleted=False
            ).exists():
                raise serializers.ValidationError("شما قبلاً برای این مربی نظر داده‌اید.")
        
        # جلوگیری از پاسخ تو در تو
        if reply_to:
            if reply_to.reply_to is not None:
                raise serializers.ValidationError("فقط می‌توانید به نظرات اصلی پاسخ دهید.")
        
        return data
    
    def validate_comment(self, value):
        """فیلتر فحش‌ها در متن کامنت"""
        badwords_path = os.path.join(settings.BASE_DIR, 'badwords_fa.json')
        
        if not os.path.exists(badwords_path):
            return value
        
        with open(badwords_path, 'r', encoding='utf-8') as f:
            bad_words = json.load(f)
        
        text = value.lower().replace("‌", "").replace(" ", "")
        
        for word in bad_words:
            w = word.strip().lower().replace("‌", "").replace(" ", "")
            if w and w in text:
                raise serializers.ValidationError("در متن شما کلمات نامناسب وجود دارد.")
        
        return value


class TrainerReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer برای ایجاد نظر مربی"""
    class Meta:
        model = TrainerReview
        fields = [
            'trainer',
            'rating',
            'comment',
            'reply_to',
        ]
    
    def create(self, validated_data):
        """ایجاد نظر جدید"""
        user = self.context['request'].user
        trainer = validated_data['trainer']
        
        validated_data['user'] = user
        
        # بررسی سابقه خرید از مربی (اگر لازم باشد)
        # has_purchased = hasattr(user, "trainer_purchases") and ...
        # validated_data['buyer'] = has_purchased
        
        return super().create(validated_data)
