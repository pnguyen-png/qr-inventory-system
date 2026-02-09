from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import csv
import urllib.parse
import os
from .models import InventoryItem, StatusHistory, ItemPhoto, NotificationLog


def scanner_landing(request):
    """Main QR scanner landing page"""
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

        history = item.status_history.all()
        photos = item.photos.all()
        status_labels = dict(item.STATUS_CHOICES)

        return render(request, 'inventory/scanner_landing.html', {
            'item': item,
            'history': history,
            'photos': photos,
            'status_labels': status_labels,
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
    """Endpoint to update item status with checkout attribution and audit trail"""
    try:
        item_id = request.POST.get('item_id')
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        changed_by = request.POST.get('changed_by', '')

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

        # Checkout attribution
        if status_value == 'checked_out':
            item.checked_out_by = changed_by
            item.checked_out_at = timezone.now()
        elif old_status == 'checked_out' and status_value != 'checked_out':
            item.checked_out_by = ''
            item.checked_out_at = None

        item.save()

        # Record status change history with audit trail
        StatusHistory.objects.create(
            item=item,
            old_status=old_status,
            new_status=status_value,
            notes=notes,
            changed_by=changed_by,
        )

        # Send notification for checkout or damage
        _send_notification(item, old_status, status_value, changed_by)

        return JsonResponse({
            'success': True,
            'status': new_status,
            'last_updated': item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _send_notification(item, old_status, new_status, changed_by):
    """Send webhook notifications for checkout/damage events"""
    webhook_url = os.environ.get('NOTIFICATION_WEBHOOK_URL', '')
    notification_type = None
    message = ''

    if new_status == 'checked_out':
        notification_type = 'checkout'
        message = f'{item.manufacturer} Box #{item.box_id} checked out by {changed_by or "unknown"}'
    elif item.damaged and old_status != new_status:
        notification_type = 'damaged'
        message = f'{item.manufacturer} Box #{item.box_id} (DAMAGED) status changed to {dict(InventoryItem.STATUS_CHOICES).get(new_status, new_status)}'
    elif old_status != new_status:
        notification_type = 'status_change'
        message = f'{item.manufacturer} Box #{item.box_id} status: {dict(InventoryItem.STATUS_CHOICES).get(old_status, old_status)} -> {dict(InventoryItem.STATUS_CHOICES).get(new_status, new_status)}'

    if notification_type:
        NotificationLog.objects.create(
            item=item,
            notification_type=notification_type,
            message=message,
            sent_to=webhook_url or 'logged_only',
        )

        if webhook_url:
            try:
                import requests
                requests.post(webhook_url, json={
                    'type': notification_type,
                    'message': message,
                    'item_id': item.id,
                    'manufacturer': item.manufacturer,
                    'box_id': item.box_id,
                    'pallet_id': item.pallet_id,
                    'changed_by': changed_by,
                }, timeout=5)
            except Exception:
                pass  # Don't fail the status update if notification fails


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
    show_archived = request.GET.get('archived', '') == '1'

    if show_archived:
        items = InventoryItem.objects.filter(archived=True).order_by('-archived_at')
    else:
        items = InventoryItem.objects.filter(archived=False).order_by('-updated_at')

    all_active = InventoryItem.objects.filter(archived=False)
    overdue_items = [i for i in all_active if i.is_overdue]

    return render(request, 'inventory/dashboard.html', {
        'items': items,
        'checked_in_count': all_active.filter(status='checked_in').count(),
        'checked_out_count': all_active.filter(status='checked_out').count(),
        'damaged_count': all_active.filter(damaged=True).count(),
        'archived_count': InventoryItem.objects.filter(archived=True).count(),
        'overdue_count': len(overdue_items),
        'overdue_items': overdue_items,
        'show_archived': show_archived,
    })


def item_history(request, item_id):
    """Item history view"""
    item = get_object_or_404(InventoryItem, id=item_id)
    history = item.status_history.all()
    return render(request, 'inventory/item_history.html', {'item': item, 'history': history})


@csrf_exempt
@require_http_methods(["POST"])
def update_history_notes(request):
    """Update notes on a status history entry"""
    try:
        history_id = request.POST.get('history_id')
        notes = request.POST.get('notes', '')

        entry = get_object_or_404(StatusHistory, id=history_id)
        entry.notes = notes
        entry.save()

        return JsonResponse({'success': True, 'notes': entry.notes})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def bulk_update_status(request):
    """Bulk update status for multiple items"""
    try:
        data = json.loads(request.body)
        item_ids = data.get('item_ids', [])
        new_status = data.get('status', '')
        notes = data.get('notes', '')
        changed_by = data.get('changed_by', '')

        if not item_ids or not new_status:
            return JsonResponse({'success': False, 'error': 'Missing item_ids or status'}, status=400)

        valid_statuses = dict(InventoryItem.STATUS_CHOICES)
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)

        updated = 0
        for item in InventoryItem.objects.filter(id__in=item_ids):
            old_status = item.status
            item.status = new_status

            if new_status == 'checked_out':
                item.checked_out_by = changed_by
                item.checked_out_at = timezone.now()
            elif old_status == 'checked_out':
                item.checked_out_by = ''
                item.checked_out_at = None

            item.save()

            StatusHistory.objects.create(
                item=item,
                old_status=old_status,
                new_status=new_status,
                notes=notes or 'Bulk status update',
                changed_by=changed_by,
            )
            _send_notification(item, old_status, new_status, changed_by)
            updated += 1

        return JsonResponse({'success': True, 'updated_count': updated})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def export_csv(request):
    """Export inventory to CSV"""
    show_archived = request.GET.get('archived', '') == '1'

    if show_archived:
        items = InventoryItem.objects.filter(archived=True).order_by('-updated_at')
    else:
        items = InventoryItem.objects.filter(archived=False).order_by('-updated_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory_export.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Manufacturer', 'Pallet ID', 'Box ID', 'Contents', 'Damaged',
        'Location', 'Description', 'Status', 'Checked Out By', 'Checked Out At',
        'Created', 'Updated', 'Archived'
    ])

    status_labels = dict(InventoryItem.STATUS_CHOICES)

    for item in items:
        writer.writerow([
            item.id,
            item.manufacturer,
            item.pallet_id,
            item.box_id,
            item.content,
            'Yes' if item.damaged else 'No',
            item.location,
            item.description,
            status_labels.get(item.status, item.status),
            item.checked_out_by,
            item.checked_out_at.strftime('%Y-%m-%d %H:%M') if item.checked_out_at else '',
            item.created_at.strftime('%Y-%m-%d %H:%M'),
            item.updated_at.strftime('%Y-%m-%d %H:%M'),
            'Yes' if item.archived else 'No',
        ])

    return response


def export_pdf(request):
    """Export inventory to a simple HTML-based printable report (PDF-ready)"""
    show_archived = request.GET.get('archived', '') == '1'

    if show_archived:
        items = InventoryItem.objects.filter(archived=True).order_by('-updated_at')
    else:
        items = InventoryItem.objects.filter(archived=False).order_by('-updated_at')

    return render(request, 'inventory/export_pdf.html', {
        'items': items,
        'generated_at': timezone.now(),
        'status_labels': dict(InventoryItem.STATUS_CHOICES),
    })


@csrf_exempt
@require_http_methods(["POST"])
def archive_item(request):
    """Archive or unarchive an item"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        archive = data.get('archive', True)

        item = get_object_or_404(InventoryItem, id=item_id)
        item.archived = archive
        item.archived_at = timezone.now() if archive else None
        item.save()

        return JsonResponse({'success': True, 'archived': item.archived})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def bulk_archive(request):
    """Archive multiple items at once"""
    try:
        data = json.loads(request.body)
        item_ids = data.get('item_ids', [])
        archive = data.get('archive', True)

        now = timezone.now() if archive else None
        updated = InventoryItem.objects.filter(id__in=item_ids).update(
            archived=archive,
            archived_at=now,
        )

        return JsonResponse({'success': True, 'updated_count': updated})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_photo(request):
    """Upload a photo for an item"""
    try:
        item_id = request.POST.get('item_id')
        caption = request.POST.get('caption', '')
        uploaded_by = request.POST.get('uploaded_by', '')

        if not item_id:
            return JsonResponse({'success': False, 'error': 'Missing item_id'}, status=400)

        item = get_object_or_404(InventoryItem, id=item_id)

        if 'photo' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No photo file provided'}, status=400)

        photo = ItemPhoto.objects.create(
            item=item,
            image=request.FILES['photo'],
            caption=caption,
            uploaded_by=uploaded_by,
        )

        return JsonResponse({
            'success': True,
            'photo_id': photo.id,
            'url': photo.image.url,
            'caption': photo.caption,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def delete_photo(request):
    """Delete a photo"""
    try:
        data = json.loads(request.body)
        photo_id = data.get('photo_id')

        photo = get_object_or_404(ItemPhoto, id=photo_id)
        photo.image.delete(save=False)
        photo.delete()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def overdue_items_api(request):
    """API endpoint returning overdue checked-out items"""
    items = InventoryItem.objects.filter(
        status='checked_out',
        checked_out_at__isnull=False,
        archived=False,
    )

    overdue = []
    for item in items:
        if item.is_overdue:
            overdue.append({
                'id': item.id,
                'manufacturer': item.manufacturer,
                'pallet_id': item.pallet_id,
                'box_id': item.box_id,
                'checked_out_by': item.checked_out_by,
                'checked_out_at': item.checked_out_at.isoformat(),
                'days_out': item.days_checked_out,
            })

    return JsonResponse({'overdue_items': overdue, 'count': len(overdue)})


def inventory_report_api(request):
    """API endpoint for scheduled inventory report data"""
    active = InventoryItem.objects.filter(archived=False)
    status_labels = dict(InventoryItem.STATUS_CHOICES)

    status_counts = {}
    for key, label in InventoryItem.STATUS_CHOICES:
        status_counts[label] = active.filter(status=key).count()

    overdue = [i for i in active if i.is_overdue]

    return JsonResponse({
        'total_items': active.count(),
        'status_breakdown': status_counts,
        'damaged_count': active.filter(damaged=True).count(),
        'overdue_count': len(overdue),
        'archived_count': InventoryItem.objects.filter(archived=True).count(),
        'generated_at': timezone.now().isoformat(),
    })
