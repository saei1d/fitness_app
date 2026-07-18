from accounts.imports import *
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from gyms.models import Gym
from packages.models import GroupPackage, Package
from gyms.serializers import GymSerializer
from packages.serializers import PackageSerializer
from collections import defaultdict
from django.db.models import Subquery, OuterRef, Min
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from gyms.models import Gym
from packages.models import Package
from django.db.models import Q
import random


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
        # ساب‌کوئری برای پیدا کردن کمترین قیمت پکیج هر باشگاه
        cheapest_package = Package.objects.filter(
            group_package__gym=OuterRef('pk')
        ).order_by('price').values('price')[:1]

        # Sort by order_homepage first (if > 0), then by average_rating
        gyms = (
            Gym.objects
            .annotate(price=Subquery(cheapest_package))
            .order_by('-order_homepage', '-average_rating')[:10]
        )

        data = GymSerializer(gyms, many=True, context={'request': request}).data
        return Response(data)




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

        groups = list(groups_qs)
        if not groups:
            return Response([])  # یا می‌تونی fallback بذاری

        # جمع‌آوری پکیج‌ها بر اساس gym_id (مقاوم در برابر gym به صورت id یا آبجکت)
        gym_packages_map = defaultdict(list)  # key = gym_id, value = list of package instances
        gym_max_order_map = {}  # key = gym_id, value = max order_homepage of packages
        gym_ids = set()
        for group in groups:
            # اگر select_related('gym') انجام شده، group.gym ممکن است آبجکت باشد
            gym_id = getattr(group, 'gym_id', None) or (getattr(group, 'gym', None) and getattr(group.gym, 'id', None))
            if gym_id is None:
                continue
            gym_ids.add(gym_id)
            # استفاده از related name یا attribute برای گرفتن پکیج‌های گروه
            # Sort packages by order_homepage first (if > 0), then by default
            packages = list(group.packages.all())
            try:
                packages.sort(key=lambda p: (-p.order_homepage if p.order_homepage > 0 else 0, p.id))
                # Track max order_homepage for this gym
                max_order = max([p.order_homepage for p in packages if p.order_homepage > 0] or [0])
                gym_max_order_map[gym_id] = max(gym_max_order_map.get(gym_id, 0), max_order)
            except AttributeError:
                # If order_homepage field doesn't exist yet (migration not run), use default sorting
                packages.sort(key=lambda p: p.id)
                gym_max_order_map[gym_id] = 0
            gym_packages_map[gym_id].extend(packages)

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

        # Sort gyms by highest order_homepage of their packages, then by gym order_homepage, then random for ties
        gyms_data.sort(key=lambda g: (
            -gym_max_order_map.get(g['id'], 0),  # Highest package order_homepage
            -g.get('order_homepage', 0),  # Gym's own order_homepage
            hash(str(g['id']))  # Random tiebreaker
        ))

        # Limit to 10 gyms
        gyms_data = gyms_data[:10]

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


