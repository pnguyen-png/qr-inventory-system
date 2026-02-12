from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'inventory'

urlpatterns = [
    # Root redirect to dashboard
    path('', RedirectView.as_view(url='/dashboard/', permanent=False), name='home'),

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

    # Edit item
    path('api/edit-item/', views.edit_item, name='edit_item'),

    # Photos
    path('api/upload-photo/', views.upload_photo, name='upload_photo'),
    path('api/delete-photo/', views.delete_photo, name='delete_photo'),

    # Next pallet ID
    path('api/next-pallet/', views.next_pallet_api, name='next_pallet'),

    # Archive
    path('api/archive-item/', views.archive_item, name='archive_item'),

    # Labeled QR code image download
    path('qr/<int:item_id>/labeled.png', views.generate_labeled_qr, name='generate_labeled_qr'),

    # Pallet-specific QR download
    path('export/pallet-qr/<str:manufacturer>/<str:pallet_id>/', views.download_pallet_qr, name='download_pallet_qr'),

    # Export
    path('export/qr-codes/', views.export_qr_codes, name='export_qr_codes'),
    path('export/csv/', views.export_csv, name='export_csv'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),

    # Reports & alerts
    path('api/overdue/', views.overdue_items_api, name='overdue_items'),
    path('api/report/', views.inventory_report_api, name='inventory_report'),
]
