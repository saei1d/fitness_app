# Generated manually to version the initial schema.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('discount', '0001_initial'),
        ('packages', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Purchase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('buyer_code', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('purchase_date', models.DateTimeField(auto_now_add=True)),
                ('expire_date', models.DateTimeField(blank=True, null=True)),
                ('payment_status', models.CharField(choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('verification_status', models.CharField(choices=[('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('total_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('commission_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('net_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('final_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_code', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='discount_code', to='discount.discountcode')),
                ('package', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to='packages.package')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchases', to=settings.AUTH_USER_MODEL)),
                ('verified_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='verified_purchases', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.OneToOneField(limit_choices_to={'role': 'owner'}, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('type', models.CharField(choices=[('credit', 'Credit'), ('debit', 'Debit')], default='credit', max_length=6)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('payment_id', models.BigIntegerField(blank=True, null=True)),
                ('description', models.TextField(blank=True, help_text='توضیحات تراکنش')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin_wallet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='finance.adminwallet')),
                ('purchase', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='finance.purchase')),
                ('wallet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='finance.wallet')),
            ],
        ),
        migrations.CreateModel(
            name='WithdrawRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('completed', 'Completed')], default='pending', max_length=20)),
                ('description', models.TextField(blank=True, help_text='توضیحات درخواست برداشت')),
                ('admin_message', models.TextField(blank=True, help_text='پیام ادمین درباره وضعیت درخواست')),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_withdraw_requests', to=settings.AUTH_USER_MODEL)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdraw_requests', to=settings.AUTH_USER_MODEL)),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdraw_requests', to='finance.wallet')),
            ],
        ),
    ]
