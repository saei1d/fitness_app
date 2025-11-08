from django.apps import AppConfig


class GymsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gyms'
    verbose_name = 'باشگاه‌ها'
    
    def ready(self):
        import gyms.admin
