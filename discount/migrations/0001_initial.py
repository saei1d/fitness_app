# Generated manually to version the initial schema.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gyms', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscountCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='کد تخفیف')),
                ('discount_type', models.CharField(choices=[('percent', 'درصدی'), ('amount', 'مبلغ ثابت')], max_length=10, verbose_name='نوع تخفیف')),
                ('value', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='مقدار تخفیف')),
                ('source_type', models.CharField(choices=[('club', 'از سهم باشگاه'), ('admin', 'از سهم ادمین')], max_length=10, verbose_name='نوع کسر تخفیف')),
                ('start_date', models.DateTimeField(blank=True, null=True, verbose_name='شروع اعتبار')),
                ('end_date', models.DateTimeField(blank=True, null=True, verbose_name='پایان اعتبار')),
                ('usage_limit', models.PositiveIntegerField(blank=True, null=True, verbose_name='تعداد مجاز کل استفاده')),
                ('used_count', models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده‌شده')),
                ('per_user_limit', models.PositiveIntegerField(blank=True, null=True, verbose_name='تعداد مجاز استفاده هر کاربر')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('club', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='gyms.gym', verbose_name='باشگاه مرتبط (درصورت وجود)')),
            ],
            options={'verbose_name': 'کد تخفیف', 'verbose_name_plural': 'کدهای تخفیف', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='DiscountUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('used_at', models.DateTimeField(auto_now_add=True)),
                ('discount', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='discount.discountcode')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'استفاده از کد تخفیف', 'verbose_name_plural': 'استفاده‌های کاربران از کد تخفیف'},
        ),
        migrations.AddIndex(model_name='discountusage', index=models.Index(fields=['discount', 'user'], name='discount_di_discoun_5b82ab_idx')),
    ]
