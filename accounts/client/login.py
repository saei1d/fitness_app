from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from datetime import timedelta
from accounts.serializers import RequestOTPSerializer, VerifyOTPSerializer, CompleteRegistrationSerializer
from accounts.models import User, OTP
import random
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

OTP_TTL_SECONDS = 300


def send_sms_fake(phone, code):
    print(f"[FAKE SMS] To: {phone}, OTP: {code}")


class RequestOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']

        code = f"{random.randint(0, 999999):06d}"
        now = timezone.now()
        otp = OTP.objects.create(
            phone=phone,
            code=code,
            created_at=now,
            expires_at=now + timedelta(seconds=OTP_TTL_SECONDS)
        )

        user, created = User.objects.get_or_create(phone=phone)

        send_sms_fake(phone, code)

        return Response({
            "detail": "OTP sent (test).",
            "is_new_user": created
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        code = serializer.validated_data['code']

        otps = OTP.objects.filter(phone=phone, is_used=False).order_by('-created_at')
        if not otps.exists():
            return Response({"detail": "OTP not found or already used."}, status=status.HTTP_400_BAD_REQUEST)
        otp = otps.first()
        if otp.is_expired():
            return Response({"detail": "OTP expired."}, status=status.HTTP_400_BAD_REQUEST)
        if otp.code != code:
            return Response({"detail": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        otp.is_used = True
        otp.save()

        user, created = User.objects.get_or_create(phone=phone)

        user.is_phone_verified = True
        user.save()

        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        refresh_token = str(refresh)

        is_profile_complete = bool(user.first_name and user.last_name and user.birthdate and user.has_usable_password())

        return Response({
            "access": access,
            "refresh": refresh_token,
            "is_profile_complete": is_profile_complete,
            "user": {
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "birthdate": user.birthdate,
                "is_phone_verified": user.is_phone_verified
            }
        }, status=status.HTTP_200_OK)


class CompleteRegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # باید با توکن احراز هویت شده باشد

    def post(self, request):
        serializer = CompleteRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        first_name = serializer.validated_data['first_name']
        last_name = serializer.validated_data['last_name']
        birthdate = serializer.validated_data['birthdate']
        password = serializer.validated_data['password']

        user.first_name = first_name
        user.last_name = last_name
        user.birthdate = birthdate
        user.set_password(password)
        user.save()

        return Response({
            "detail": "Profile completed.",
            "user": {
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "birthdate": user.birthdate
            }
        }, status=status.HTTP_200_OK)
