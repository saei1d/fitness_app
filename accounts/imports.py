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
from drf_spectacular.utils import extend_schema
import string
import random