from django.contrib import admin
from .models import InventoryItem, StatusHistory, ItemPhoto, NotificationLog, ChangeLog, ScanLog, DeletionLog

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['box_id', 'manufacturer', 'pallet_id', 'status', 'location', 'checked_out_by', 'archived']
    list_filter = ['status', 'archived', 'damaged']
    search_fields = ['manufacturer', 'pallet_id', 'location', 'checked_out_by']

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['item', 'old_status', 'new_status', 'changed_by', 'changed_at']
    list_filter = ['new_status']
    search_fields = ['changed_by', 'notes']

@admin.register(ItemPhoto)
class ItemPhotoAdmin(admin.ModelAdmin):
    list_display = ['item', 'caption', 'uploaded_by', 'uploaded_at']

@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ['item', 'notification_type', 'sent_at', 'sent_to']
    list_filter = ['notification_type']

@admin.register(ChangeLog)
class ChangeLogAdmin(admin.ModelAdmin):
    list_display = ['item', 'change_type', 'field_name', 'old_value', 'new_value', 'changed_by', 'changed_at']
    list_filter = ['change_type', 'field_name']
    search_fields = ['changed_by', 'old_value', 'new_value']

@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ['item', 'scanned_at']
    list_filter = ['scanned_at']

@admin.register(DeletionLog)
class DeletionLogAdmin(admin.ModelAdmin):
    list_display = ['manufacturer', 'pallet_id', 'item_count', 'deleted_by', 'deleted_at']
    list_filter = ['deleted_by', 'deleted_at']
    search_fields = ['manufacturer', 'pallet_id', 'deleted_by']
    readonly_fields = ['manufacturer', 'pallet_id', 'item_count', 'item_ids', 'deleted_by', 'deleted_at', 'details']
