# Generated manually to version the initial schema.

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import gyms.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Gym',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('address', models.CharField(blank=True, max_length=512)),
                ('working_hours', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('average_rating', models.FloatField(default=0.0)),
                ('comments', models.IntegerField(default=0)),
                ('banner', models.ImageField(blank=True, null=True, upload_to='gyms/banners/')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Gym', 'verbose_name_plural': 'Gyms', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='GymImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to=gyms.models.gym_image_upload_path)),
                ('alt_text', models.CharField(blank=True, max_length=255)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='gyms.gym')),
            ],
            options={'ordering': ['order', 'uploaded_at']},
        ),
    ]
