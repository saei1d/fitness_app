from django.urls import path
from .staffuser import UserStaff
from .users_list import UsersList

urlpatterns = [
    path('make-this-user-staff/', UserStaff.as_view(), name='staffuser'),
    path('users-list/', UsersList.as_view(), name='users-list'),
]
