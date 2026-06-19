from django.urls import path

from .notifications import (
    AdminSendNotificationView,
    MarkAllReadView,
    MarkNotificationReadView,
    NotificationListView,
    UnreadCountView,
)

urlpatterns = [
    path('notifications/',                NotificationListView.as_view(),         name='notification-list'),
    path('notifications/read-all/',       MarkAllReadView.as_view(),              name='notification-read-all'),
    path('notifications/unread-count/',   UnreadCountView.as_view(),              name='notification-unread-count'),
    path('notifications/admin/send/',     AdminSendNotificationView.as_view(),    name='notification-admin-send'),
    path('notifications/<int:pk>/read/',  MarkNotificationReadView.as_view(),     name='notification-read'),
]
