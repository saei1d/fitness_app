from django.urls import path
from .staffuser import UserStaff

urlpatterns = [
    path('make-this-user-staff/', UserStaff.as_view(), name='staffuser'),
]
