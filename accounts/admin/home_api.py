from accounts.imports import *
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from gyms.models import Gym
from packages.models import GroupPackage, Package
from gyms.serializers import GymSerializer
from packages.serializers import PackageSerializer
from collections import defaultdict


class GroupPackageWithPackagesSerializer(serializers.ModelSerializer):
    gym = GymSerializer(read_only=True)
    packages = PackageSerializer(many=True, read_only=True)

    class Meta:
        model = GroupPackage
        fields = ['id', 'title', 'description', 'gym', 'packages']



@extend_schema(tags=['Home'], summary='Top rated gyms', description='برگرداندن حدود ۱۰ باشگاه با بیشترین امتیاز')
class TopGymsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        gyms = Gym.objects.all().order_by('-average_rating')[:10]
        data = GymSerializer(gyms, many=True, context={'request': request}).data
        return Response(data)



from collections import defaultdict
from django.db.models import Q
import random

@extend_schema(
    tags=['Home'],
    summary='Sport group packages',
    description='بازگرداندن باشگاه‌های مرتبط با ورزش خواسته‌شده به‌صورت رندوم همراه با پکیج‌هایشان'
)
class SportGroupPackagesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        sport = request.query_params.get('sport')
        if not sport:
            return Response({'detail': 'sport query param is required (e.g., بدنسازی, پیلاتس, یوگا).'}, status=400)

        # فیلتر روی group packages (عنوان و توضیحات و همچنین پکیج‌ها)
        groups_qs = (
            GroupPackage.objects
            .filter(
                Q(title__icontains=sport) |
                Q(description__icontains=sport) |
                Q(packages__title__icontains=sport) |
                Q(packages__description__icontains=sport)
            )
            .distinct()
            .select_related('gym')
            .prefetch_related('packages')
        )

        # اگر رندوم می‌خوایم و دیتابیس بزرگه: بهتره در پایتون رندوم کنیم
        groups = list(groups_qs)
        if not groups:
            return Response([])  # یا می‌تونی fallback بذاری

        random.shuffle(groups)
        groups = groups[:10]  # محدودسازی بعد از shuffle در پایتون امن‌تر است

        # جمع‌آوری پکیج‌ها بر اساس gym_id (مقاوم در برابر gym به صورت id یا آبجکت)
        gym_packages_map = defaultdict(list)  # key = gym_id, value = list of package instances
        gym_ids = set()
        for group in groups:
            # اگر select_related('gym') انجام شده، group.gym ممکن است آبجکت باشد
            gym_id = getattr(group, 'gym_id', None) or (getattr(group, 'gym', None) and getattr(group.gym, 'id', None))
            if gym_id is None:
                continue
            gym_ids.add(gym_id)
            # استفاده از related name یا attribute برای گرفتن پکیج‌های گروه
            for package in group.packages.all():
                gym_packages_map[gym_id].append(package)

        # واکشی همه‌ی Gymها یک‌جا (برای جلوگیری از N+1)
        gyms = Gym.objects.filter(id__in=gym_ids)

        gyms_data = []
        gym_by_id = {g.id: g for g in gyms}
        for gid in gym_ids:
            gym_obj = gym_by_id.get(gid)
            if not gym_obj:
                continue
            gym_data = GymSerializer(gym_obj, context={'request': request}).data
            packages = gym_packages_map.get(gid, [])
            gym_data['packages'] = PackageSerializer(packages, many=True).data
            gyms_data.append(gym_data)

        return Response(gyms_data)

@extend_schema(
    tags=['Home'],
    summary='Home search',
    description='جستجو در نام باشگاه، نام GroupPackage و نام پکیج. پارامتر q الزامی است.'
)
class HomeSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return Response({'detail': 'q query param is required.'}, status=400)

        gyms = Gym.objects.filter(name__icontains=q)[:5]
        groups = (
            GroupPackage.objects
            .filter(title__icontains=q)
            .select_related('gym')[:5]
        )
        packages = (
            Package.objects
            .filter(title__icontains=q)
            .select_related('group_package', 'group_package__gym')[:5]
        )

        return Response({
            'gyms': GymSerializer(gyms, many=True).data,
            'group_packages': GroupPackageWithPackagesSerializer(groups, many=True).data,
            'packages': PackageSerializer(packages, many=True).data,
        })


