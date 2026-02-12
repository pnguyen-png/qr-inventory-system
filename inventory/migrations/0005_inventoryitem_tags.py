from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_inventoryitem_project_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryitem',
            name='tags',
            field=models.TextField(blank=True, default=''),
        ),
    ]
