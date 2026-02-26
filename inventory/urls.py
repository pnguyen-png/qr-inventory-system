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
    path('shipments/', views.shipment_history, name='shipment_history'),
    path('shipment/<str:manufacturer>/<str:pallet_id>/', views.shipment_detail, name='shipment_detail'),
    path('tags/', views.tag_management, name='tag_management'),

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
    path('api/bulk-edit/', views.bulk_edit, name='bulk_edit'),

    # Edit item
    path('api/edit-item/', views.edit_item, name='edit_item'),

    # Photos
    path('api/upload-photo/', views.upload_photo, name='upload_photo'),
    path('api/delete-photo/', views.delete_photo, name='delete_photo'),

    # Tags
    path('api/rename-tag/', views.rename_tag, name='rename_tag'),
    path('api/delete-tag/', views.delete_tag, name='delete_tag'),
    path('api/create-tag/', views.create_tag, name='create_tag'),
    path('api/toggle-tag-favorite/', views.toggle_tag_favorite, name='toggle_tag_favorite'),

    # Next pallet ID
    path('api/next-pallet/', views.next_pallet_api, name='next_pallet'),

    # Archive & delete
    path('api/archive-item/', views.archive_item, name='archive_item'),
    path('api/delete-pallet/', views.delete_pallet, name='delete_pallet'),

    # Print jobs (wireless printing to Brother QL-820NWB)
    path('api/print-jobs/create/', views.create_print_jobs, name='create_print_jobs'),
    path('api/print-jobs/pending/', views.pending_print_jobs, name='pending_print_jobs'),
    path('api/print-jobs/<int:job_id>/update-status/', views.update_print_job_status, name='update_print_job_status'),
    path('api/print-jobs/<int:job_id>/label.png', views.print_job_label_image, name='print_job_label_image'),
    path('api/print-jobs/<int:job_id>/status/', views.print_job_status, name='print_job_status'),

    # QR code images (local generation)
    path('qr/<int:item_id>/code.png', views.generate_qr_image, name='generate_qr_image'),
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
