from accounts.imports import *
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from gyms.models import Gym
from packages.models import GroupPackage, Package
from gyms.serializers import GymSerializer
from packages.serializers import PackageSerializer


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


@extend_schema(
    tags=['Home'],
    summary='Sport group packages',
    description='بازگرداندن گروه‌های پکیج مرتبط با ورزش خواسته‌شده (بدنسازی/پیلاتس/یوگا) به‌صورت رندوم همراه با پکیج‌های زیرمجموعه'
)
class SportGroupPackagesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        sport = request.query_params.get('sport')
        if not sport:
            return Response({'detail': 'sport query param is required (e.g., بدنسازی, پیلاتس, یوگا).'}, status=400)

        # انتخاب رندوم بین باشگاه‌ها با استفاده از order_by('?') و محدودسازی
        groups = (
            GroupPackage.objects
            .filter(title__icontains=sport)
            .select_related('gym')
            .prefetch_related('packages')
            .order_by('?')[:10]
        )

        serializer = GroupPackageWithPackagesSerializer(groups, many=True)
        return Response(serializer.data)


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


