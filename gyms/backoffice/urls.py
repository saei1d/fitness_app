from django.urls import path
from .operators import (
    GymOperatorListView,
    GymOperatorCreateView,
    GymOperatorDetailView,
    ChangeUserRoleView
)


urlpatterns = [
    # لیست همه متصدی‌ها
    path('operators/', GymOperatorListView.as_view(), name='gym-operators-list'),
    
    # ایجاد متصدی جدید
    path('operators/create/', GymOperatorCreateView.as_view(), name='gym-operator-create'),
    
    # جزئیات، به‌روزرسانی و حذف متصدی
    path('operators/<int:pk>/', GymOperatorDetailView.as_view(), name='gym-operator-detail'),
    
    # تغییر role کاربر
    path('change-role/', ChangeUserRoleView.as_view(), name='change-user-role'),
]
