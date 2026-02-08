# inventory/api_views.py
# Add this NEW file to handle API requests from Excel

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
import os
import urllib.parse
from .models import InventoryItem

@csrf_exempt  # Allows Excel to send requests without CSRF token
@require_http_methods(["POST"])
def create_item_from_excel(request):
    """
    API endpoint to create inventory items from Excel
    
    Expected POST data:
    {
        "manufacturer": "ACME Corp",
        "pallet_id": "PLT-001",
        "box_id": 1,
        "content": 50,
        "damaged": false,
        "location": "Warehouse A",
        "description": "Electronic components"
    }
    
    Returns:
    {
        "success": true,
        "item_id": 1,
        "qr_url": "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=...",
        "scanner_url": "http://127.0.0.1:8000/scan/?data=..."
    }
    """
    try:
        # Parse JSON data from Excel
        data = json.loads(request.body)
        
        # Extract fields
        manufacturer = data.get('manufacturer', '')
        pallet_id = data.get('pallet_id', '')
        box_id = int(data.get('box_id', 0))
        content = int(data.get('content', 0))
        damaged = data.get('damaged', False)
        location = data.get('location', '')
        description = data.get('description', '')
        
        # Validate required fields
        if not all([manufacturer, pallet_id, box_id]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: manufacturer, pallet_id, or box_id'
            }, status=400)
        
        # Build barcode payload
        barcode_payload = f"MFR={manufacturer} | PALLET={pallet_id} | BOX={box_id}"
        
        # Build scanner URL
        encoded_payload = urllib.parse.quote(barcode_payload)
        base_url = os.environ.get("SITE_URL", "https://web-production-57c20.up.railway.app")
        scanner_url = f"{base_url}/scan/?data={encoded_payload}"
        
        # Build QR code URL
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(scanner_url)}"
        
        # Check if item already exists
        existing_item = InventoryItem.objects.filter(
            manufacturer=manufacturer,
            pallet_id=pallet_id,
            box_id=box_id
        ).first()
        
        if existing_item:
            # Update existing item
            existing_item.content = content
            existing_item.damaged = damaged
            existing_item.location = location
            existing_item.description = description
            existing_item.barcode_payload = barcode_payload
            existing_item.qr_url = qr_url
            existing_item.save()
            
            return JsonResponse({
                'success': True,
                'item_id': existing_item.id,
                'qr_url': qr_url,
                'scanner_url': scanner_url,
                'barcode_payload': barcode_payload,
                'message': 'Item updated successfully'
            })
        else:
            # Create new item
            item = InventoryItem.objects.create(
                manufacturer=manufacturer,
                pallet_id=pallet_id,
                box_id=box_id,
                content=content,
                damaged=damaged,
                location=location,
                description=description,
                status='checked_in',  # Default status
                barcode_payload=barcode_payload,
                qr_url=qr_url
            )
            
            return JsonResponse({
                'success': True,
                'item_id': item.id,
                'qr_url': qr_url,
                'scanner_url': scanner_url,
                'barcode_payload': barcode_payload,
                'message': 'Item created successfully'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': f'Invalid data format: {str(e)}'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def bulk_create_items(request):
    """
    API endpoint to create multiple items at once
    
    Expected POST data:
    {
        "items": [
            {
                "manufacturer": "ACME Corp",
                "pallet_id": "PLT-001",
                "box_id": 1,
                "content": 50,
                "damaged": false,
                "location": "Warehouse A",
                "description": "Components"
            },
            ...
        ]
    }
    """
    try:
        data = json.loads(request.body)
        items_data = data.get('items', [])
        
        if not items_data:
            return JsonResponse({
                'success': False,
                'error': 'No items provided'
            }, status=400)
        
        created_items = []
        errors = []
        
        for idx, item_data in enumerate(items_data):
            try:
                manufacturer = item_data.get('manufacturer', '')
                pallet_id = item_data.get('pallet_id', '')
                box_id = int(item_data.get('box_id', 0))
                content = int(item_data.get('content', 0))
                damaged = item_data.get('damaged', False)
                location = item_data.get('location', '')
                description = item_data.get('description', '')
                
                if not all([manufacturer, pallet_id, box_id]):
                    errors.append({
                        'index': idx,
                        'error': 'Missing required fields'
                    })
                    continue
                
                barcode_payload = f"MFR={manufacturer} | PALLET={pallet_id} | BOX={box_id}"
                encoded_payload = urllib.parse.quote(barcode_payload)
                base_url = os.environ.get("SITE_URL", "https://web-production-57c20.up.railway.app")
                scanner_url = f"{base_url}/scan/?data={encoded_payload}"
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(scanner_url)}"
                
                # Check if exists
                existing = InventoryItem.objects.filter(
                    manufacturer=manufacturer,
                    pallet_id=pallet_id,
                    box_id=box_id
                ).first()
                
                if existing:
                    existing.content = content
                    existing.damaged = damaged
                    existing.location = location
                    existing.description = description
                    existing.barcode_payload = barcode_payload
                    existing.qr_url = qr_url
                    existing.save()
                    item = existing
                else:
                    item = InventoryItem.objects.create(
                        manufacturer=manufacturer,
                        pallet_id=pallet_id,
                        box_id=box_id,
                        content=content,
                        damaged=damaged,
                        location=location,
                        description=description,
                        status='checked_in',
                        barcode_payload=barcode_payload,
                        qr_url=qr_url
                    )
                
                created_items.append({
                    'item_id': item.id,
                    'qr_url': qr_url,
                    'scanner_url': scanner_url
                })
                
            except Exception as e:
                errors.append({
                    'index': idx,
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'created_count': len(created_items),
            'error_count': len(errors),
            'items': created_items,
            'errors': errors
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
