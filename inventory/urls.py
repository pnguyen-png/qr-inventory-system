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
    
    # Status update (HTMX)
    path('api/update-status/', views.update_status, name='update_status'),
    path('api/update-notes/', views.update_history_notes, name='update_history_notes'),
    path('api/items/', views.item_api, name='item_api'),
]