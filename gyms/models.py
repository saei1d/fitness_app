from django.conf import settings
from django.db import models
from django.contrib.gis.db import models as gis_models
from accounts.models import User
import os
from django.utils.text import slugify

class Gym(gis_models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = gis_models.PointField(srid=4326)
    address = models.CharField(max_length=512, blank=True)
    working_hours = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    average_rating = models.FloatField(default=0.0)
    comments = models.IntegerField(default=0)
    banner = models.ImageField(upload_to="gyms/banners/", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Gym"
        verbose_name_plural = "Gyms"

    def __str__(self):
        return f"{self.name} (owner={self.owner})"

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None





def gym_image_upload_path(instance, filename):
    gym_id = str(instance.gym.id)
    return os.path.join("gyms", "images", gym_id, filename)


class GymImage(models.Model):
    gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=gym_image_upload_path)
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "uploaded_at"]

    def __str__(self):
        return f"Image {self.id} for {self.gym.name}"