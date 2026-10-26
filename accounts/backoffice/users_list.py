from accounts.imports import *
from accounts.permissions import is_platform_admin
from accounts.serializers import UserDetailSerializer
from drf_spectacular.utils import extend_schema

class UsersList(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(
        request=dict,
        responses={200: dict},
        description="لیست کاربران"
    )
    
    def get(self, request):
        if not is_platform_admin(request.user):
            return Response({'detail': 'شما مجوز دسترسی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all()
        serializer = UserDetailSerializer(users, many=True)
        return Response(serializer.data)