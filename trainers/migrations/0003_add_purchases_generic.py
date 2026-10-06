from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('trainers', '0002_add_contact_method'),
    ]

    operations = [
        # GenericRelation doesn't create a database field
        # It's just a reverse relation wrapper
        # So we don't need to add anything to the database
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
