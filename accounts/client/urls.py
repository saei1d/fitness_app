from django.urls import path
from .login import *
from .profile import EditProfileView
from .referral import EnterReferralCodeView

urlpatterns = [
    path('request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('check-auth/',CheckAuth.as_view(),name='checkauth'),
    path('profile/', EditProfileView.as_view(), name='my-profile'),
    path('profile/<int:user_id>/', EditProfileView.as_view(), name='user-profile'),
    path('enter-referral-code/', EnterReferralCodeView.as_view(), name='enter-referral-code'),
    ]
