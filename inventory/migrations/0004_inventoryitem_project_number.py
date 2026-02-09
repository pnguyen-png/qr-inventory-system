from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_new_features'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryitem',
            name='project_number',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
