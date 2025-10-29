from accounts.imports import *


@extend_schema(tags=['Admin'])
class UserStaff(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Admin'],
        request={
            'type': 'object',
            'properties': {
                'phone': {'type': 'string', 'description': 'شماره تلفن کاربر'},
                'is_staff': {'type': 'boolean', 'description': 'تنظیم وضعیت staff'}
            },
            'required': ['phone']
        },
        responses={200: dict, 400: dict, 403: dict, 404: dict},
        summary='تنظیم وضعیت Staff کاربر',
        description='تنها سوپریوزر می‌تواند وضعیت staff کاربر را تنظیم کند'
    )
    def post(self, request):
        if not request.user.is_superuser:
            return Response({"detail": "Only superuser allowed"}, status=status.HTTP_403_FORBIDDEN)

        phone = request.data.get('phone')
        make_staff = request.data.get('is_staff', True)
        if phone is None:
            return Response({"phone": "Phone is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        target_user.is_staff = bool(make_staff)
        target_user.save()
        return Response({
            "phone": target_user.phone,
            "is_staff": target_user.is_staff
        }, status=status.HTTP_200_OK)