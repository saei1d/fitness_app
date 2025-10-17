from django.urls import path
from .login import *
from .profile import EditProfileView

urlpatterns = [
    path('request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('profile/', EditProfileView.as_view(), name='my-profile'),
    path('profile/<int:user_id>/', EditProfileView.as_view(), name='user-profile'),
    ]
