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
from trainers.models import Trainer
from trainers.serializers import TrainerSerializer


class GroupPackageWithPackagesSerializer(serializers.ModelSerializer):
    packages = PackageSerializer(many=True, read_only=True)

    class Meta:
        model = GroupPackage
        fields = ['id', 'title', 'description', 'packages']



@extend_schema(tags=['Home'], summary='Top rated gyms', description='برگرداندن حدود ۱۰ باشگاه با بیشترین امتیاز')
class TopGymsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # ساب‌کوئری برای پیدا کردن کمترین قیمت پکیج هر باشگاه
        cheapest_package = Package.objects.filter(
            gym=OuterRef('pk')
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

        # فیلتر روی پکیج‌ها (عنوان و توضیحات و همچنین گروه پکیج)
        packages_qs = (
            Package.objects
            .filter(
                Q(title__icontains=sport) |
                Q(description__icontains=sport) |
                Q(group_package__title__icontains=sport) |
                Q(group_package__description__icontains=sport)
            )
            .distinct()
            .select_related('gym', 'group_package')
        )

        packages = list(packages_qs)
        if not packages:
            return Response([])

        # جمع‌آوری پکیج‌ها بر اساس gym_id
        gym_packages_map = defaultdict(list)  # key = gym_id, value = list of package instances
        gym_max_order_map = {}  # key = gym_id, value = max order_homepage of packages
        gym_ids = set()
        for package in packages:
            gym_id = package.gym_id
            gym_ids.add(gym_id)
            # Sort packages by order_homepage first (if > 0), then by default
            try:
                order_homepage = package.order_homepage if hasattr(package, 'order_homepage') else 0
                gym_packages_map[gym_id].append(package)
                # Track max order_homepage for this gym
                if order_homepage > 0:
                    gym_max_order_map[gym_id] = max(gym_max_order_map.get(gym_id, 0), order_homepage)
            except AttributeError:
                gym_packages_map[gym_id].append(package)
                gym_max_order_map[gym_id] = 0

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
            # Sort packages by order_homepage first (if > 0), then by default
            try:
                packages.sort(key=lambda p: (-p.order_homepage if p.order_homepage > 0 else 0, p.id))
            except AttributeError:
                packages.sort(key=lambda p: p.id)
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
            .filter(title__icontains=q)[:5]
        )
        packages = (
            Package.objects
            .filter(title__icontains=q)
            .select_related('gym', 'group_package')[:5]
        )

        return Response({
            'gyms': GymSerializer(gyms, many=True).data,
            'group_packages': GroupPackageWithPackagesSerializer(groups, many=True).data,
            'packages': PackageSerializer(packages, many=True).data,
        })


@extend_schema(
    tags=['Home'],
    summary='Top trainers',
    description='برگرداندن مربی‌ها به ترتیب order_homepage'
)
class TopTrainersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Sort by order_homepage first (if > 0), then by average_rating
        trainers = Trainer.objects.filter(
            is_active=True
        ).order_by('-order_homepage', '-average_rating')[:10]

        data = TrainerSerializer(trainers, many=True).data
        return Response(data)


