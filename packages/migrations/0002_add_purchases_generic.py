from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('packages', '0001_initial'),
    ]

    operations = [
        # GenericRelation doesn't create a database field
        # It's just a reverse relation wrapper
        # So we don't need to add anything to the database
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
