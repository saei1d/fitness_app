from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'اعلانات'

    def ready(self):
        import notifications.signals  # noqa: F401 — registers all handlers
