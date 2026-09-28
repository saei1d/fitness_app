# Generated migration to add trainer role to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('customer', 'Customer'),
                    ('owner', 'Owner'),
                    ('admin', 'Admin'),
                    ('operator', 'Operator'),
                    ('trainer', 'Trainer'),
                ],
                default='customer',
                max_length=20
            ),
        ),
    ]
