from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='statushistory',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='statushistory',
            name='item',
            field=models.ForeignKey(
                on_delete=models.deletion.CASCADE,
                related_name='status_history',
                to='inventory.inventoryitem',
            ),
        ),
        migrations.AlterModelOptions(
            name='statushistory',
            options={'ordering': ['-changed_at']},
        ),
    ]
