from django.db import models
from django.utils import timezone
from datetime import timedelta


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

    # Checkout attribution
    checked_out_by = models.CharField(max_length=255, blank=True, default='')
    checked_out_at = models.DateTimeField(null=True, blank=True)

    # Archiving
    archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"

    def __str__(self):
        return f"{self.manufacturer} - Box {self.box_id}"

    def get_damaged_display(self):
        return "Yes" if self.damaged else "No"

    @property
    def is_overdue(self):
        if self.status == 'checked_out' and self.checked_out_at:
            return timezone.now() - self.checked_out_at > timedelta(days=7)
        return False

    @property
    def days_checked_out(self):
        if self.status == 'checked_out' and self.checked_out_at:
            return (timezone.now() - self.checked_out_at).days
        return 0


class StatusHistory(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20)
    new_status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, default='')
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-changed_at']

    STATUS_LABELS = dict(InventoryItem.STATUS_CHOICES)

    def __str__(self):
        return f"{self.item} - {self.old_status} to {self.new_status}"

    def old_status_label(self):
        return self.STATUS_LABELS.get(self.old_status, self.old_status)

    def new_status_label(self):
        return self.STATUS_LABELS.get(self.new_status, self.new_status)


class ItemPhoto(models.Model):
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='item_photos/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Photo for {self.item} - {self.uploaded_at}"


class NotificationLog(models.Model):
    NOTIFICATION_TYPES = [
        ('checkout', 'Item Checked Out'),
        ('damaged', 'Item Damaged'),
        ('overdue', 'Overdue Checkout'),
        ('status_change', 'Status Changed'),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_to = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.item}"
