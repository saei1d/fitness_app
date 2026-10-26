from django.db import migrations, models

import accounts.validators


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_trainer_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='card_number',
            field=models.CharField(
                blank=True,
                default=None,
                help_text='شماره کارت بانکی کاربر برای تسویه حساب (۱۶ تا ۲۰ رقم)',
                max_length=20,
                null=True,
                validators=[accounts.validators.validate_card_number],
            ),
        ),
    ]
