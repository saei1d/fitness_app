# Generated manually.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='notification',
            new_name='notificatio_recipie_a972ce_idx',
            old_name='notificatio_recipie_created_idx',
        ),
        migrations.RenameIndex(
            model_name='notification',
            new_name='notificatio_recipie_4e3567_idx',
            old_name='notificatio_recipie_is_read_idx',
        ),
        migrations.RenameIndex(
            model_name='notification',
            new_name='notificatio_notific_f2898f_idx',
            old_name='notificatio_notif_type_idx',
        ),
    ]
