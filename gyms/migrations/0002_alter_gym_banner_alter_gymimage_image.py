# Generated manually.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('gyms', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gym',
            name='banner',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='gyms/banners/',
            ),
        ),
        migrations.AlterField(
            model_name='gymimage',
            name='image',
            field=models.ImageField(upload_to=''),
        ),
    ]
