# Generated migration to add trainer discount models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('discount', '0002_package_discount'),
        ('trainers', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrainerDiscountCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='کد تخفیف')),
                ('discount_type', models.CharField(choices=[('percent', 'درصدی'), ('amount', 'مبلغ ثابت')], max_length=10, verbose_name='نوع تخفیف')),
                ('value', models.DecimalField(decimal_places=2, help_text='برای درصدی: عدد کامل وارد کنید (مثلاً 5 برای 5٪) - برای مبلغ ثابت: مبلغ را به تومان وارد کنید', max_digits=10, verbose_name='مقدار تخفیف')),
                ('source_type', models.CharField(choices=[('trainer', 'از سهم مربی'), ('admin', 'از سهم ادمین')], max_length=10, verbose_name='نوع کسر تخفیف')),
                ('start_date', models.DateTimeField(blank=True, null=True, verbose_name='شروع اعتبار')),
                ('end_date', models.DateTimeField(blank=True, null=True, verbose_name='پایان اعتبار')),
                ('usage_limit', models.PositiveIntegerField(blank=True, null=True, verbose_name='تعداد مجاز کل استفاده')),
                ('used_count', models.PositiveIntegerField(default=0, verbose_name='تعداد استفاده‌شده')),
                ('per_user_limit', models.PositiveIntegerField(blank=True, null=True, verbose_name='تعداد مجاز استفاده هر کاربر')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('packages', models.ManyToManyField(blank=True, related_name='discount_codes', to='trainers.trainerpackage', verbose_name='پکیج‌های مرتبط')),
                ('trainer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='trainers.trainer', verbose_name='مربی مرتبط (درصورت وجود)')),
            ],
            options={
                'verbose_name': 'کد تخفیف مربی',
                'verbose_name_plural': 'کدهای تخفیف مربی',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TrainerDiscountUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('used_at', models.DateTimeField(auto_now_add=True)),
                ('discount', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='discount.trainerdiscountcode')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'استفاده از کد تخفیف مربی',
                'verbose_name_plural': 'استفاده‌های کاربران از کد تخفیف مربی',
            },
        ),
        migrations.CreateModel(
            name='TrainerPackageDiscount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('discount_type', models.CharField(choices=[('percent', 'درصدی'), ('amount', 'مبلغ ثابت')], max_length=10, verbose_name='نوع تخفیف')),
                ('value', models.DecimalField(decimal_places=2, help_text='برای درصدی: عدد کامل وارد کنید (مثلاً 5 برای 5٪) - برای مبلغ ثابت: مبلغ را به تومان وارد کنید', max_digits=10, verbose_name='مقدار تخفیف')),
                ('source_type', models.CharField(choices=[('trainer', 'از سهم مربی'), ('admin', 'از سهم ادمین')], max_length=10, verbose_name='نوع کسر تخفیف')),
                ('start_date', models.DateTimeField(blank=True, null=True, verbose_name='شروع اعتبار')),
                ('end_date', models.DateTimeField(blank=True, null=True, verbose_name='پایان اعتبار')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discounts', to='trainers.trainerpackage', verbose_name='پکیج مربی')),
            ],
            options={
                'verbose_name': 'تخفیف پکیج مربی',
                'verbose_name_plural': 'تخفیف‌های پکیج مربی',
                'ordering': ['-created_at'],
            },
        ),
    ]
