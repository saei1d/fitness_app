from django.db import migrations
from django.contrib.contenttypes.fields import GenericRelation


class Migration(migrations.Migration):

    dependencies = [
        ('trainers', '0002_add_contact_method'),
    ]

    operations = [
        migrations.AddField(
            model_name='trainerpackage',
            name='purchases_generic',
            field=GenericRelation(
                'finance.Purchase',
                content_type_field='content_type',
                object_id_field='object_id',
                related_query_name='trainer_package_generic'
            ),
        ),
    ]
