from rest_framework import serializers
from .models import GymImage, Gym
from django.contrib.gis.geos import Point
from .models import Gym
from accounts.serializers import UserDetailSerializer
from django.utils import timezone
from discount.models import *
from packages.serializers import PackageSerializer
from django.db import models

class GymImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(use_url=True)

    class Meta:
        model = GymImage
        fields = ["id", "image", "alt_text", "order", "uploaded_at"]

# سریالایزر برای آپلود تصاویر (تکی یا چندتایی)
class GymImageFlexibleSerializer(serializers.Serializer):
    gym = serializers.IntegerField(required=True, help_text="شناسه باشگاه")
    images = serializers.ListField(
        child=serializers.ImageField(), required=False, help_text="لیست تصاویر برای آپلود چندتایی"
    )
    image = serializers.ImageField(required=False, help_text="تصویر تکی")
    alt_texts = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False, help_text="لیست متن‌های جایگزین برای تصاویر چندتایی"
    )
    alt_text = serializers.CharField(required=False, allow_blank=True, help_text="متن جایگزین برای تصویر تکی")

    def validate(self, attrs):
        if not attrs.get("image") and not attrs.get("images"):
            raise serializers.ValidationError("حداقل یک تصویر لازم است.")
        gym_id = attrs.get("gym")
        if not Gym.objects.filter(id=gym_id).exists():
            raise serializers.ValidationError("باشگاه موردنظر وجود ندارد.")
        return attrs
    
    
    
class GymSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_discount = serializers.SerializerMethodField()  # فیلد جدید برای بیشترین تخفیف    owner = serializers.CharField(write_only=True)
    owner_data = UserDetailSerializer(source='owner', read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    latitude_input = serializers.FloatField(write_only=True, required=False)
    longitude_input = serializers.FloatField(write_only=True, required=False)
    images = serializers.SerializerMethodField()
    package = serializers.SerializerMethodField()
    distance_meters = serializers.SerializerMethodField(read_only=True,null=True,blank=True)



    class Meta:
        model = Gym
        fields = [
            "id", "owner", "owner_data", "name", "description", "address",
            "working_hours", "banner", "latitude", "longitude",
            "latitude_input", "longitude_input",
            "comments", "average_rating", "price","max_discount","images", "package","distance_meters"
        ]

    def get_images(self, obj):
        request = self.context.get('request')
        images = obj.images.all().order_by('order', 'uploaded_at')  # استفاده از related_name='images'
        image_urls = []
        for img in images:
            if img.image and hasattr(img.image, 'url'):
                url = img.image.url
                if request:
                    url = request.build_absolute_uri(url)
                image_urls.append({
                    "id": img.id,
                    "url": url,
                    "alt_text": img.alt_text or "",
                    "order": img.order
                })
        return image_urls
    
    def get_latitude(self, obj):
        """برگرداندن عرض جغرافیایی از location"""
        return float(obj.latitude) if obj.latitude else None
    
    def get_longitude(self, obj):
        """برگرداندن طول جغرافیایی از location"""
        return float(obj.longitude) if obj.longitude else None
    
    def get_distance_meters(self, obj):
        if hasattr(obj, 'distance') and obj.distance:
            return round(obj.distance.m, 2)  # دو رقم اعشار برای نمایش تمیزتر
        return None
    
    def get_package(self, obj):
        """برگرداندن تمام پکیج‌های باشگاه"""
        all_packages = []
        # گرفتن تمام GroupPackage های این باشگاه
        group_packages = obj.group_packages.all().prefetch_related('packages')
        
        for group_package in group_packages:
            # گرفتن تمام پکیج‌های هر گروه
            packages = group_package.packages.all()
            for package in packages:
                all_packages.append(package)
        
        # سریالایز کردن تمام پکیج‌ها
        return PackageSerializer(all_packages, many=True).data
    
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        request = self.context.get('request')
        if instance.banner and hasattr(instance.banner, 'url'):
            rep['banner'] = request.build_absolute_uri(instance.banner.url) if request else instance.banner.url
        else:
            rep['banner'] = None
        return rep

    def get_max_discount(self, obj):
        # دریافت تاریخ فعلی
        now = timezone.now()

        # فیلتر کردن کدهای تخفیف فعال و معتبر برای این باشگاه
        discounts = DiscountCode.objects.filter(
            club=obj,  # مرتبط با این باشگاه
            is_active=True,  # کد فعال باشد
            start_date__lte=now,  # شروع اعتبار قبل از حالا
            end_date__gte=now,  # پایان اعتبار بعد از حالا
            used_count__lt=models.F('usage_limit')  # تعداد استفاده کمتر از حد مجاز
        ).exclude(usage_limit__isnull=True)  # کدهایی که محدودیت استفاده دارند

        if not discounts.exists():
            return None  # اگر تخفیفی نبود، null برگردون

        # پیدا کردن بیشترین تخفیف
        max_discount = None
        max_value = 0

        for discount in discounts:
            # برای تخفیف درصدی، مقدار رو به عنوان درصد در نظر می‌گیریم
            # برای تخفیف مبلغی، مستقیماً مقدار رو مقایسه می‌کنیم
            current_value = float(discount.value) if discount.discount_type == 'amount' else float(discount.value)
            
            if current_value > max_value:
                max_value = current_value
                max_discount = {
                    'code': discount.code,
                    'type': discount.discount_type,
                    'value': float(discount.value),  # تبدیل به float برای JSON
                    'start_date': discount.start_date,
                    'end_date': discount.end_date
                }

        return max_discount
    def create(self, validated_data):
        latitude = validated_data.pop("latitude_input", None)
        longitude = validated_data.pop("longitude_input", None)
        if latitude and longitude:
            validated_data["location"] = Point(float(longitude), float(latitude), srid=4326)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        latitude = validated_data.pop("latitude_input", None)
        longitude = validated_data.pop("longitude_input", None)
        if latitude and longitude:
            validated_data["location"] = Point(float(longitude), float(latitude), srid=4326)
        return super().update(instance, validated_data)
