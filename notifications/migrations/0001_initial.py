# Generated manually to version the initial schema.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('notification_type', models.CharField(
                    choices=[
                        ('purchase', 'Purchase'),
                        ('plan_activated', 'Plan Activated'),
                        ('plan_expired', 'Plan Expired'),
                        ('ticket_reply', 'Ticket Reply'),
                        ('ticket_created', 'Ticket Created'),
                        ('withdraw_request', 'Withdraw Request'),
                    ],
                    max_length=30,
                )),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField(max_length=2000)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('data', models.JSONField(blank=True, default=None, null=True)),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', '-created_at'], name='notificatio_recipie_created_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['recipient', 'is_read'], name='notificatio_recipie_is_read_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['notification_type'], name='notificatio_notif_type_idx'),
        ),
    ]
