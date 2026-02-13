import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_inventoryitem_tags'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('change_type', models.CharField(choices=[('created', 'Item Created'), ('field_edit', 'Field Edited')], default='field_edit', max_length=20)),
                ('field_name', models.CharField(max_length=100)),
                ('old_value', models.TextField(blank=True, default='')),
                ('new_value', models.TextField(blank=True, default='')),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.CharField(blank=True, default='', max_length=255)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='change_logs', to='inventory.inventoryitem')),
            ],
            options={
                'ordering': ['-changed_at'],
            },
        ),
    ]
