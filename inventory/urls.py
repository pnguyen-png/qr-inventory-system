from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Web pages
    path('scan/', views.scanner_landing, name='scanner_landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('item/<int:item_id>/history/', views.item_history, name='item_history'),

    # Shipment form (replaces Microsoft Form + Excel script)
    path('add-shipment/', views.add_shipment, name='add_shipment'),
    path('shipment/<str:shipment_key>/download/excel/', views.download_shipment_excel, name='download_shipment_excel'),
    path('shipment/<str:shipment_key>/download/csv/', views.download_shipment_csv, name='download_shipment_csv'),

    # Status update
    path('api/update-status/', views.update_status, name='update_status'),
    path('api/update-notes/', views.update_history_notes, name='update_history_notes'),
    path('api/items/', views.item_api, name='item_api'),

    # Bulk operations
    path('api/bulk-update-status/', views.bulk_update_status, name='bulk_update_status'),
    path('api/bulk-archive/', views.bulk_archive, name='bulk_archive'),

    # Archive
    path('api/archive-item/', views.archive_item, name='archive_item'),

    # Export
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),

    # Reports & alerts
    path('api/overdue/', views.overdue_items_api, name='overdue_items'),
    path('api/report/', views.inventory_report_api, name='inventory_report'),
]
