from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import urllib.parse
from .models import InventoryItem


def scanner_landing(request):
    """
    Main QR scanner landing page
    """
    barcode_data = request.GET.get('data', '')
    
    if not barcode_data:
        return render(request, 'inventory/scanner_landing.html', {
            'error': 'Invalid QR code. No data found.',
            'item': None,
            'item_json': '{}'
        })
    
    try:
        decoded_data = urllib.parse.unquote(barcode_data)
        parts = decoded_data.split(' | ')
        data_dict = {}
        
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                data_dict[key.strip()] = value.strip()
        
        manufacturer = data_dict.get('MFR', '')
        pallet_id = data_dict.get('PALLET', '')
        box_id = data_dict.get('BOX', '')
        
        item = get_object_or_404(
            InventoryItem,
            manufacturer=manufacturer,
            pallet_id=pallet_id,
            box_id=int(box_id)
        )
        
        import json
        item_data = {
            'id': item.id,
            'manufacturer': item.manufacturer,
            'pallet_id': item.pallet_id,
            'box_id': item.box_id,
            'content': item.content,
            'damaged': item.get_damaged_display(),
            'location': item.location,
            'description': item.description,
            'status': dict(item.STATUS_CHOICES).get(item.status, 'Unknown'),
            'last_updated': item.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return render(request, 'inventory/scanner_landing.html', {
            'item': item,
            'item_json': json.dumps(item_data),
            'error': None
        })
        
    except Exception as e:
        return render(request, 'inventory/scanner_landing.html', {
            'error': f'Error loading item: {str(e)}',
            'item': None,
            'item_json': '{}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def update_status(request):
    """HTMX endpoint to update item status"""
    try:
        item_id = request.POST.get('item_id')
        new_status = request.POST.get('status')
        
        status_mapping = {
            'Checked In': 'checked_in',
            'Checked Out': 'checked_out',
            'Tested': 'tested',
            'Will Be Reused': 'will_be_reused',
            'Recycling': 'recycling',
        }
        
        status_value = status_mapping.get(new_status)
        if not status_value:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
        
        item = get_object_or_404(InventoryItem, id=item_id)
        old_status = item.status
        item.status = status_value
        item.save()

        # Record status change history
        from .models import StatusHistory
        StatusHistory.objects.create(
            item=item,
            old_status=old_status,
            new_status=status_value,
        )
        
        return JsonResponse({
            'success': True,
            'status': new_status,
            'last_updated': item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def item_api(request):
    """API endpoint to get item information"""
    manufacturer = request.GET.get('mfr', '')
    pallet_id = request.GET.get('pallet', '')
    box_id = request.GET.get('box', '')
    
    if not all([manufacturer, pallet_id, box_id]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        item = get_object_or_404(
            InventoryItem,
            manufacturer=manufacturer,
            pallet_id=pallet_id,
            box_id=int(box_id)
        )
        
        return JsonResponse({
            'id': item.id,
            'manufacturer': item.manufacturer,
            'pallet_id': item.pallet_id,
            'box_id': item.box_id,
            'content': item.content,
            'damaged': item.get_damaged_display(),
            'location': item.location,
            'description': item.description,
            'status': dict(item.STATUS_CHOICES).get(item.status, 'Unknown'),
            'last_updated': item.updated_at.isoformat(),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def dashboard(request):
    """Dashboard view with full inventory listing"""
    items = InventoryItem.objects.all().order_by('-updated_at')
    return render(request, 'inventory/dashboard.html', {
        'items': items,
        'checked_in_count': items.filter(status='checked_in').count(),
        'checked_out_count': items.filter(status='checked_out').count(),
        'damaged_count': items.filter(damaged=True).count(),
    })


def item_history(request, item_id):
    """Item history view"""
    from .models import StatusHistory
    item = get_object_or_404(InventoryItem, id=item_id)
    history = StatusHistory.objects.filter(item=item).order_by('-changed_at')
    return render(request, 'inventory/item_history.html', {'item': item, 'history': history})