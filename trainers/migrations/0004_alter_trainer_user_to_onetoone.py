from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainers', '0003_add_purchases_generic'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainer',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name='trainer_profile',
                to='accounts.user'
            ),
        ),
    ]
