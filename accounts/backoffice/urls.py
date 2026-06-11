from django.urls import path
from .staffuser import UserStaff
from .users_list import UsersList
from .home_api import TopGymsView, SportGroupPackagesView, HomeSearchView

urlpatterns = [
    path('make-this-user-staff/', UserStaff.as_view(), name='staffuser'),
    path('users-list/', UsersList.as_view(), name='users-list'),
    path('home/top-gyms/', TopGymsView.as_view(), name='home-top-gyms'),
    path('home/sport-groups/', SportGroupPackagesView.as_view(), name='home-sport-groups'),
    path('home/search/', HomeSearchView.as_view(), name='home-search'),
]
