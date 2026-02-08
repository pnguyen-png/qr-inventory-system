from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('manufacturer', models.CharField(max_length=255)),
                ('pallet_id', models.CharField(max_length=100)),
                ('box_id', models.IntegerField()),
                ('content', models.IntegerField()),
                ('damaged', models.BooleanField(default=False)),
                ('location', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('checked_in', 'Checked In'), ('checked_out', 'Checked Out'), ('tested', 'Tested'), ('will_be_reused', 'Will Be Reused'), ('recycling', 'Recycling')], default='checked_in', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('barcode_payload', models.CharField(max_length=500, unique=True)),
                ('qr_url', models.URLField(max_length=500)),
            ],
            options={
                'verbose_name': 'Inventory Item',
                'verbose_name_plural': 'Inventory Items',
            },
        ),
        migrations.CreateModel(
            name='StatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('old_status', models.CharField(max_length=20)),
                ('new_status', models.CharField(max_length=20)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='inventory.inventoryitem')),
            ],
        ),
    ]
