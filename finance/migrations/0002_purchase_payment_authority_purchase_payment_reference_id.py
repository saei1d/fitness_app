from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchase',
            name='payment_authority',
            field=models.CharField(blank=True, max_length=128, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='purchase',
            name='payment_reference_id',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
