from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_statushistory_notes'),
    ]

    operations = [
        # Checkout attribution fields on InventoryItem
        migrations.AddField(
            model_name='inventoryitem',
            name='checked_out_by',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='inventoryitem',
            name='checked_out_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Archiving fields on InventoryItem
        migrations.AddField(
            model_name='inventoryitem',
            name='archived',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='inventoryitem',
            name='archived_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        # Audit trail: who changed status
        migrations.AddField(
            model_name='statushistory',
            name='changed_by',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        # ItemPhoto model
        migrations.CreateModel(
            name='ItemPhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='item_photos/%Y/%m/')),
                ('caption', models.CharField(blank=True, default='', max_length=255)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('uploaded_by', models.CharField(blank=True, default='', max_length=255)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='inventory.inventoryitem')),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
        # NotificationLog model
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('checkout', 'Item Checked Out'), ('damaged', 'Item Damaged'), ('overdue', 'Overdue Checkout'), ('status_change', 'Status Changed')], max_length=20)),
                ('message', models.TextField()),
                ('sent_at', models.DateTimeField(auto_now_add=True)),
                ('sent_to', models.CharField(blank=True, default='', max_length=500)),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='inventory.inventoryitem')),
            ],
            options={
                'ordering': ['-sent_at'],
            },
        ),
    ]
