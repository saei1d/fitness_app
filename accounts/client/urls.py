from django.urls import path
from .login import *

urlpatterns = [
    path('request-otp/', RequestOTPView.as_view(), name='request-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('edit-profile/', EditProfileView.as_view(), name='edit-profile'),
]
