# Generated manually.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('discount', '0001_initial'),
        ('packages', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='discountcode',
            old_name='club',
            new_name='gym',
        ),
        migrations.AddField(
            model_name='discountcode',
            name='packages',
            field=models.ManyToManyField(
                blank=True,
                related_name='discount_codes',
                to='packages.Package',
                verbose_name='پکیج‌های مرتبط',
            ),
        ),
        migrations.RemoveIndex(
            model_name='discountusage',
            name='discount_di_discoun_5b82ab_idx',
        ),
    ]
