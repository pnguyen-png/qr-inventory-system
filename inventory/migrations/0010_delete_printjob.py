from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0009_printjob'),
    ]

    operations = [
        migrations.DeleteModel(
            name='PrintJob',
        ),
    ]
