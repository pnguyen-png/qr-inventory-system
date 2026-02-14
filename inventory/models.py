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
    project_number = models.CharField(max_length=100, blank=True, default='')
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

    # Tags (comma-separated keywords)
    tags = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"

    def __str__(self):
        return f"{self.manufacturer} - Box {self.box_id}"

    def get_damaged_display(self):
        return "Yes" if self.damaged else "No"

    @property
    def tag_id(self):
        return f"FRA-P{self.pallet_id}-B{self.box_id}"

    @property
    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(',') if t.strip()]

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


class ChangeLog(models.Model):
    CHANGE_TYPES = [
        ('created', 'Item Created'),
        ('field_edit', 'Field Edited'),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='change_logs')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPES, default='field_edit')
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, default='')
    new_value = models.TextField(blank=True, default='')
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-changed_at']

    FIELD_LABELS = {
        'content': 'Contents (Qty)',
        'damaged': 'Damaged',
        'location': 'Location',
        'description': 'Description',
        'project_number': 'Project Number',
        'manufacturer': 'Manufacturer',
        'tags': 'Tags',
        'status': 'Status',
        'archived': 'Archived',
    }

    def __str__(self):
        return f"{self.item} - {self.field_name}: {self.old_value} -> {self.new_value}"

    def field_label(self):
        return self.FIELD_LABELS.get(self.field_name, self.field_name)


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


class ScanLog(models.Model):
    """Tracks each time an item's QR code is scanned."""
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='scan_logs')
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-scanned_at']

    def __str__(self):
        return f"Scan of {self.item} at {self.scanned_at}"


class Tag(models.Model):
    """Standalone tag that can exist before being assigned to items."""
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


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
