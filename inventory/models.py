from django.db import models

class InventoryItem(models.Model):
    STATUS_CHOICES = [
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('tested', 'Tested'),
        ('will_be_reused', 'Will Be Reused'),
        ('recycling', 'Recycling'),
    ]
    
    manufacturer = models.CharField(max_length=255)
    pallet_id = models.CharField(max_length=100)
    box_id = models.IntegerField()
    content = models.IntegerField()
    damaged = models.BooleanField(default=False)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='checked_in')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    barcode_payload = models.CharField(max_length=500, unique=True)
    qr_url = models.URLField(max_length=500)
    
    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
    
    def __str__(self):
        return f"{self.manufacturer} - Box {self.box_id}"
    
    def get_damaged_display(self):
        return "Yes" if self.damaged else "No"

class StatusHistory(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, default='')
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']

    STATUS_LABELS = dict(InventoryItem.STATUS_CHOICES)

    def __str__(self):
        return f"{self.item} - {self.old_status} to {self.new_status}"

    def old_status_label(self):
        return self.STATUS_LABELS.get(self.old_status, self.old_status)

    def new_status_label(self):
        return self.STATUS_LABELS.get(self.new_status, self.new_status)