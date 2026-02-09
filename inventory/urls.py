from django.urls import path
from . import views, api_views

app_name = 'inventory'

urlpatterns = [
    # Web pages
    path('scan/', views.scanner_landing, name='scanner_landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('item/<int:item_id>/history/', views.item_history, name='item_history'),

    # API endpoints for Excel
    path('api/create-item/', api_views.create_item_from_excel, name='create_item_api'),
    path('api/bulk-create/', api_views.bulk_create_items, name='bulk_create_api'),

    # Status update
    path('api/update-status/', views.update_status, name='update_status'),
    path('api/update-notes/', views.update_history_notes, name='update_history_notes'),
    path('api/items/', views.item_api, name='item_api'),

    # Bulk operations
    path('api/bulk-update-status/', views.bulk_update_status, name='bulk_update_status'),
    path('api/bulk-archive/', views.bulk_archive, name='bulk_archive'),

    # Archive
    path('api/archive-item/', views.archive_item, name='archive_item'),

    # Photos
    path('api/upload-photo/', views.upload_photo, name='upload_photo'),
    path('api/delete-photo/', views.delete_photo, name='delete_photo'),

    # Export
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),

    # Reports & alerts
    path('api/overdue/', views.overdue_items_api, name='overdue_items'),
    path('api/report/', views.inventory_report_api, name='inventory_report'),
]
