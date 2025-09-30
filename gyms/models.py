from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from accounts.models import User


class Gym(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)]
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)]
    )
    address = models.CharField(max_length=512, blank=True)
    working_hours = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    banner = models.ImageField(upload_to="gyms/banners/", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Gym"
        verbose_name_plural = "Gyms"

    def __str__(self):
        return f"{self.name} (owner={self.owner})"


class GymImage(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="gyms/images/")
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "uploaded_at"]

    def __str__(self):
        return f"Image {self.id} for {self.gym.name}"
