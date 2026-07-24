from django.db import models
from gyms.models import Gym

class GroupPackage(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="group_packages")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.gym.name}"


class Package(models.Model):
    group_package = models.ForeignKey(GroupPackage, on_delete=models.CASCADE, related_name="packages")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    gender = models.CharField(max_length=100, choices=[('male', 'Male'), ('female', 'Female')])
    price = models.DecimalField(max_digits=15, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in days")
    commission_rate = models.FloatField(help_text="Commission rate 0.05 is 5 percent", default=0.05)
    sessions = models.IntegerField(default=0, help_text="Number of sessions")
    order_homepage = models.IntegerField(default=0, help_text="Order for homepage display (0 = use default sorting)")
    dedicated = models.BooleanField(default=False, help_text="پکیج اختصاصی برای باشگاه")



    def __str__(self):
        gender_display = self.get_gender_display()
        short_desc = (self.description[:50] + '...') if len(self.description) > 50 else self.description
        gym_name = self.group_package.gym.name
        return f"{self.title} ({gender_display}) - {gym_name} - {short_desc}"
