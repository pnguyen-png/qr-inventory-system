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
    favorite = models.BooleanField(default=False)
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


class PrintJob(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('printed', 'Printed'),
        ('failed', 'Failed'),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='print_jobs')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    printed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PrintJob #{self.id} - {self.item} ({self.status})"


class LoginAttempt(models.Model):
    """Tracks every login attempt for auditing, lockout, and rate-limiting."""
    ip_address = models.CharField(max_length=45)  # supports IPv6
    username = models.CharField(max_length=150, blank=True, default='')
    success = models.BooleanField(default=False)
    is_bot = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ip_address', 'timestamp']),
        ]

    def __str__(self):
        status = 'OK' if self.success else ('BOT' if self.is_bot else 'FAIL')
        return f"{self.ip_address} - {self.username} - {status} @ {self.timestamp}"

    # ---------- class-level helpers ----------

    LOCKOUT_THRESHOLD = 10
    LOCKOUT_WINDOW = timedelta(hours=1)
    DELAY_SCHEDULE = [0, 0, 0, 1, 2, 5, 10, 15, 20, 30]  # seconds by attempt #

    @classmethod
    def recent_failures(cls, ip):
        """Count failed (non-bot) attempts from this IP in the lockout window."""
        cutoff = timezone.now() - cls.LOCKOUT_WINDOW
        return cls.objects.filter(
            ip_address=ip, success=False, is_bot=False, timestamp__gte=cutoff
        ).count()

    @classmethod
    def is_locked_out(cls, ip):
        return cls.recent_failures(ip) >= cls.LOCKOUT_THRESHOLD

    @classmethod
    def lockout_remaining(cls, ip):
        """Return seconds remaining in lockout, or 0 if not locked out."""
        cutoff = timezone.now() - cls.LOCKOUT_WINDOW
        oldest_in_window = (
            cls.objects.filter(
                ip_address=ip, success=False, is_bot=False, timestamp__gte=cutoff
            )
            .order_by('timestamp')
            .first()
        )
        if oldest_in_window and cls.is_locked_out(ip):
            expires = oldest_in_window.timestamp + cls.LOCKOUT_WINDOW
            remaining = (expires - timezone.now()).total_seconds()
            return max(int(remaining), 0)
        return 0

    @classmethod
    def get_delay(cls, ip):
        """Progressive delay in seconds based on recent failure count."""
        failures = cls.recent_failures(ip)
        if failures >= len(cls.DELAY_SCHEDULE):
            return cls.DELAY_SCHEDULE[-1]
        return cls.DELAY_SCHEDULE[failures]

    @classmethod
    def clear_failures(cls, ip):
        """Mark recent failures as resolved by deleting them (on successful login)."""
        cutoff = timezone.now() - cls.LOCKOUT_WINDOW
        cls.objects.filter(
            ip_address=ip, success=False, timestamp__gte=cutoff
        ).delete()


class DeletionLog(models.Model):
    """Records hard-deletion of pallets for audit trail.

    No foreign key to InventoryItem so the record survives the CASCADE delete.
    """
    manufacturer = models.CharField(max_length=255)
    pallet_id = models.CharField(max_length=100)
    item_count = models.IntegerField()
    item_ids = models.TextField(blank=True, default='')
    deleted_by = models.CharField(max_length=255)
    deleted_at = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-deleted_at']

    def __str__(self):
        return f"Deleted {self.manufacturer} Pallet {self.pallet_id} ({self.item_count} items) by {self.deleted_by}"
