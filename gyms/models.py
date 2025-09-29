# # models.py
# from django.conf import settings
# from django.db import models
# from django.core.validators import MinValueValidator, MaxValueValidator
#
# # ---- Option A: simple latitude/longitude fields ----
# class Gym(models.Model):
#     id = models.BigAutoField(primary_key=True)
#     owner = models.ForeignKey(
#         settings.AUTH_USER_MODEL,
#         on_delete=models.CASCADE,
#         related_name="gyms"
#     )
#     name = models.CharField(max_length=255)
#     description = models.TextField(blank=True)
#     # simple lat/lng (use DecimalField for precision)
#     latitude = models.DecimalField(
#         max_digits=9, decimal_places=6,
#         null=True, blank=True,
#         validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)]
#     )
#     longitude = models.DecimalField(
#         max_digits=9, decimal_places=6,
#         null=True, blank=True,
#         validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)]
#     )
#     address = models.CharField(max_length=512, blank=True)
#     # working_hours as JSON: see suggested structure below
#     working_hours = models.JSONField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     # summary/banner image convenience (first image) - nullable
#     banner = models.ImageField(upload_to="gyms/banners/", null=True, blank=True)
#
#     class Meta:
#         ordering = ["-created_at"]
#         verbose_name = "Gym"
#         verbose_name_plural = "Gyms"
#
#     def __str__(self):
#         return f"{self.name} (owner={self.owner})"
#
#
# class GymImage(models.Model):
#     """
#     Stores additional banners/images for a gym.
#     """
#     gym = models.ForeignKey(Gym, on_delete=models.CASCADE, related_name="images")
#     image = models.ImageField(upload_to="gyms/images/")
#     alt_text = models.CharField(max_length=255, blank=True)
#     order = models.PositiveSmallIntegerField(default=0)
#     uploaded_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         ordering = ["order", "uploaded_at"]
#
#     def __str__(self):
#         return f"Image {self.id} for {self.gym.name}"
# -------------------------------------------------------------------------------

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from accounts.models import User


class GymGeo(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gyms_geo")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = gis_models.PointField(geography=True, null=True, blank=True)  # (lng, lat)
    address = models.CharField(max_length=512, blank=True)
    working_hours = models.JSONField(null=True, blank=True)
    banner = models.ImageField(upload_to="gyms/banners/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class GymImage(models.Model):
    gym = models.ForeignKey(GymGeo, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="gyms/images/")
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "uploaded_at"]

    def __str__(self):
        return f"Image {self.id} for {self.gym.name}"
