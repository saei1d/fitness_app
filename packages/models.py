from django.db import models

from gyms.models import Gym


# Create your models here.
class Package(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="packages")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in days")
    commission_rate = models.FloatField(help_text="Commission rate 0.05 is 5 percent", default=0.05)



    def __str__(self):
        return f"{self.title} - {self.gym.name}"
