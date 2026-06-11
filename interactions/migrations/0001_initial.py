# Generated manually to version the initial schema.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('gyms', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])),
                ('comment', models.TextField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_reported', models.BooleanField(default=False)),
                ('buyer', models.BooleanField(default=False)),
                ('blocked', models.BooleanField(default=False)),
                ('deleted', models.BooleanField(default=False)),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='gyms.gym')),
                ('reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='interactions.review')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='Favorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='gyms.gym')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='accounts.user')),
            ],
            options={'unique_together': {('user', 'gym')}},
        ),
    ]
