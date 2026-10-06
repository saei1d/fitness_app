from django.db import migrations
from django.contrib.contenttypes.fields import GenericRelation


class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='package',
            name='purchases_generic',
            field=GenericRelation(
                'finance.Purchase',
                content_type_field='content_type',
                object_id_field='object_id',
                related_query_name='package_generic'
            ),
        ),
    ]
