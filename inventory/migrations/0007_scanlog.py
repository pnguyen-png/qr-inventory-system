from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0006_changelog'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScanLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scanned_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scan_logs', to='inventory.inventoryitem')),
            ],
            options={
                'ordering': ['-scanned_at'],
            },
        ),
    ]
