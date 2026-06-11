# Generated manually to version the initial schema.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('gyms', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupPackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_packages', to='gyms.gym')),
            ],
        ),
        migrations.CreateModel(
            name='Package',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('gender', models.CharField(choices=[('male', 'Male'), ('female', 'Female')], max_length=100)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('duration', models.IntegerField(help_text='Duration in days')),
                ('commission_rate', models.FloatField(default=0.05, help_text='Commission rate 0.05 is 5 percent')),
                ('sessions', models.IntegerField(default=0, help_text='Number of sessions')),
                ('group_package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='packages', to='packages.grouppackage')),
            ],
        ),
    ]
