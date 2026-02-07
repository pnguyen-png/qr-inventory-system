from django.contrib import admin
from .models import InventoryItem, StatusHistory

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['box_id', 'manufacturer', 'pallet_id', 'status', 'location']

@admin.register(StatusHistory)  
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['item', 'old_status', 'new_status', 'changed_at']