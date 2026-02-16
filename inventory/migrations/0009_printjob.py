from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_tag'),
    ]

    operations = [
        migrations.CreateModel(
            name='PrintJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_ids', models.JSONField(help_text='List of InventoryItem IDs to print labels for')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('printing', 'Printing'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('description', models.CharField(blank=True, default='', max_length=255)),
                ('requested_by', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('printed_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, default='')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
