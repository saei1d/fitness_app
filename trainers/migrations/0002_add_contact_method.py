# Generated migration to add contact_method field to Trainer model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainer',
            name='contact_method',
            field=models.CharField(
                blank=True,
                help_text='راه ارتباطی با مربی (مثل: اینستاگرام، تلگرام، واتساپ، شماره تلفن)',
                max_length=255
            ),
        ),
    ]
