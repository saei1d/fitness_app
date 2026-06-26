from accounts.imports import *


def _profile_photo_access_allowed(user):
    return getattr(user, 'role', None) in {'customer', 'owner'}


@extend_schema(tags=['EditProfile'])
class EditProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=EditProfileSerializer,
        responses={200: dict},
        description="Edit profile"
    )
    def put(self, request, user_id=None):
        if user_id:
            if not request.user.is_staff:
                return Response({'detail': 'شما مجوز دسترسی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
            user = User.objects.filter(id=user_id).first()
            if not user:
                return Response({'detail': 'کاربر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        if ('avatar' in request.data or 'avatar' in request.FILES) and not _profile_photo_access_allowed(user):
            return Response({'detail': 'Only customer and owner roles can upload a profile photo.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = EditProfileSerializer(user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={200: UserDetailSerializer},
        description="Get user profile"
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

        serializer = UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data)


@extend_schema(tags=['ProfilePhoto'])
class ProfilePhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_user(self, request, user_id=None):
        if user_id:
            if not request.user.is_staff:
                return None, Response({'detail': 'شما مجوز دسترسی ندارید.'}, status=status.HTTP_403_FORBIDDEN)
            user = User.objects.filter(id=user_id).first()
            if not user:
                return None, Response({'detail': 'کاربر یافت نشد.'}, status=status.HTTP_404_NOT_FOUND)
            return user, None
        return request.user, None

    @extend_schema(
        responses={200: ProfilePhotoResponseSerializer},
        description="Get profile photo URL"
    )
    def get(self, request, user_id=None):
        user, error = self._get_user(request, user_id=user_id)
        if error:
            return error
        if not user.avatar:
            return Response({'avatar_url': None})
        return Response({'avatar_url': request.build_absolute_uri(user.avatar.url)})

    @extend_schema(
        request=ProfilePhotoUploadSerializer,
        responses={201: ProfilePhotoResponseSerializer},
        description="Upload or replace profile photo"
    )
    def post(self, request, user_id=None):
        user, error = self._get_user(request, user_id=user_id)
        if error:
            return error
        if not _profile_photo_access_allowed(user):
            return Response({'detail': 'Only customer and owner roles can upload a profile photo.'}, status=status.HTTP_403_FORBIDDEN)

        avatar = request.FILES.get('avatar')
        if not avatar:
            return Response({'avatar': ['This field is required.']}, status=status.HTTP_400_BAD_REQUEST)

        if user.avatar:
            user.avatar.delete(save=False)
        user.avatar = avatar
        user.save(update_fields=['avatar'])

        return Response({'avatar_url': request.build_absolute_uri(user.avatar.url)}, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={204: None},
        description="Delete profile photo"
    )
    def delete(self, request, user_id=None):
        user, error = self._get_user(request, user_id=user_id)
        if error:
            return error
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=['avatar'])
        return Response(status=status.HTTP_204_NO_CONTENT)
