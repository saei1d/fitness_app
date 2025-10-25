from accounts.imports import *
OTP_TTL_SECONDS = 300


def generate_referral_code(existing_codes):
    random_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))

    while random_code in existing_codes:
        random_code = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))

    print(f"Referral Code Generated: {random_code}")
    return random_code


def send_sms_fake(phone, code):
    print(f"[FAKE SMS] To: {phone}, OTP: {code}")


@extend_schema(tags=['Authentication'])
class RequestOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=RequestOTPSerializer,
        responses={200: dict},
        description="ارسال پیام به شماره موبایل"
    )
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
            "detail": f'OTP sent {code}',
            "is_new_user": created
        }, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentication'])
class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: dict},
        description="تایید پیام و دریافت توکن "
    )
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

        is_profile_complete = bool(user.full_name and user.birthdate and user.has_usable_password())

        return Response({
            "access": access,
            "refresh": refresh_token,
            "is_profile_complete": is_profile_complete,
            "user": {
                "phone": user.phone,
                "full_name": user.full_name,
                "birthdate": user.birthdate,
                "is_phone_verified": user.is_phone_verified
            }
        }, status=status.HTTP_200_OK)


@extend_schema(tags=['Authentication'])
class CheckAuth(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            return Response({
                "is_authenticated": True,
                "user": {
                    "id": request.user.id,
                    "phone": request.user.phone,
                    "full_name": request.user.full_name
                }
            }, status=status.HTTP_200_OK)
        return Response({
            "is_authenticated": False,
            "detail": "Invalid or expired token"
        }, status=status.HTTP_401_UNAUTHORIZED)
