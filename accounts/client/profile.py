from accounts.imports import *



@extend_schema(tags=['EditProfile'])
class EditProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EditProfileSerializer,
        responses={200: dict},
        description="ادیت پروفایل"
    )
    def put(self, request, user_id=None):
        # اگر ادمین هست یا خودش هست
        if user_id:
            if not request.user.is_staff:
                return Response({'detail': 'شما مجوز دسترسی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response({'detail': 'کاربر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        serializer = EditProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={200: UserDetailSerializer},
        description="دریافت پروفایل کاربر"
    )
    def get(self, request, user_id=None):
        if user_id:
            if not request.user.is_staff:
                return Response({'detail': 'شما مجوز دسترسی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response({'detail': 'کاربر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        serializer = UserDetailSerializer(user)
        return Response(serializer.data)