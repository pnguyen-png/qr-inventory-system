from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import csv
import urllib.parse
import os
import uuid
from .models import InventoryItem, StatusHistory, NotificationLog


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
        status_labels = dict(item.STATUS_CHOICES)

        return render(request, 'inventory/scanner_landing.html', {
            'item': item,
            'history': history,
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
        items = InventoryItem.objects.filter(archived=True).order_by('manufacturer', 'pallet_id', 'box_id')
    else:
        items = InventoryItem.objects.filter(archived=False).order_by('manufacturer', 'pallet_id', 'box_id')

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


def export_qr_codes(request):
    """Download all inventory QR codes as an Excel file"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    show_archived = request.GET.get('archived', '') == '1'

    if show_archived:
        items = InventoryItem.objects.filter(archived=True).order_by('manufacturer', 'pallet_id', 'box_id')
    else:
        items = InventoryItem.objects.filter(archived=False).order_by('manufacturer', 'pallet_id', 'box_id')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'QR Codes'

    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='8B1A1A', end_color='8B1A1A', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    headers = ['Manufacturer', 'Pallet ID', 'Box ID', 'Contents (Qty)', 'Damaged',
               'Location', 'Status', 'Barcode Payload', 'Scanner URL', 'QR Code URL']

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    base_url = os.environ.get("SITE_URL", "https://web-production-57c20.up.railway.app")
    status_labels = dict(InventoryItem.STATUS_CHOICES)

    for row_num, item in enumerate(items, 2):
        encoded_payload = urllib.parse.quote(item.barcode_payload)
        scanner_url = f"{base_url}/scan/?data={encoded_payload}"

        row_data = [
            item.manufacturer,
            item.pallet_id,
            item.box_id,
            item.content,
            'Yes' if item.damaged else 'No',
            item.location,
            status_labels.get(item.status, item.status),
            item.barcode_payload,
            scanner_url,
            item.qr_url,
        ]

        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num, value=value)
            cell.border = thin_border

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    label = 'archived' if show_archived else 'inventory'
    response['Content-Disposition'] = f'attachment; filename="qr_codes_{label}.xlsx"'
    wb.save(response)
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


# ---- Shipment Form Views ----

def add_shipment(request):
    """Single-page form to create a new shipment (replaces Microsoft Form + Excel script)"""
    if request.method == 'GET':
        return render(request, 'inventory/add_shipment.html')

    # POST — process the form
    manufacturer = request.POST.get('manufacturer', '').strip()
    pallet_id = request.POST.get('pallet_id', '').strip()
    project_number = request.POST.get('project_number', '').strip()
    num_boxes = request.POST.get('num_boxes', '').strip()
    items_per_box = request.POST.get('items_per_box', '').strip()
    location = request.POST.get('location', '').strip()
    damaged = request.POST.get('damaged', 'no')
    description = request.POST.get('description', '').strip()
    damaged_boxes_str = request.POST.get('damaged_boxes', '').strip()
    count_exceptions_str = request.POST.get('count_exceptions', '').strip()

    form_data = {
        'manufacturer': manufacturer,
        'pallet_id': pallet_id,
        'project_number': project_number,
        'num_boxes': num_boxes,
        'items_per_box': items_per_box,
        'location': location,
        'damaged': damaged,
        'description': description,
        'damaged_boxes': damaged_boxes_str,
        'count_exceptions': count_exceptions_str,
    }

    errors = []

    # Validate required fields
    if not manufacturer:
        errors.append('Manufacturer / Supplier is required.')
    if not pallet_id:
        errors.append('Pallet ID is required.')
    if not location:
        errors.append('Receiving Location is required.')

    try:
        num_boxes_int = int(num_boxes)
        if num_boxes_int < 1:
            errors.append('Number of boxes must be at least 1.')
    except (ValueError, TypeError):
        errors.append('Number of boxes must be a valid number.')
        num_boxes_int = 0

    try:
        items_per_box_int = int(items_per_box)
        if items_per_box_int < 1:
            errors.append('Items per box must be at least 1.')
    except (ValueError, TypeError):
        errors.append('Items per box must be a valid number.')
        items_per_box_int = 0

    # Parse damaged box numbers
    damaged_box_set = set()
    if damaged_boxes_str:
        for part in damaged_boxes_str.split(','):
            part = part.strip()
            if part:
                try:
                    box_num = int(part)
                    if num_boxes_int and (box_num < 1 or box_num > num_boxes_int):
                        errors.append(f'Damaged box #{box_num} is outside the range 1-{num_boxes_int}.')
                    else:
                        damaged_box_set.add(box_num)
                except ValueError:
                    errors.append(f'Invalid damaged box number: "{part}".')

    # Parse count exceptions (box:count pairs)
    count_exceptions = {}
    if count_exceptions_str:
        for part in count_exceptions_str.split(','):
            part = part.strip()
            if part:
                if ':' not in part:
                    errors.append(f'Invalid count exception format: "{part}". Use box:count (e.g. 5:30).')
                else:
                    try:
                        box_str, count_str = part.split(':', 1)
                        box_num = int(box_str.strip())
                        count_val = int(count_str.strip())
                        if num_boxes_int and (box_num < 1 or box_num > num_boxes_int):
                            errors.append(f'Exception box #{box_num} is outside the range 1-{num_boxes_int}.')
                        elif count_val < 0:
                            errors.append(f'Count for box #{box_num} cannot be negative.')
                        else:
                            count_exceptions[box_num] = count_val
                    except ValueError:
                        errors.append(f'Invalid count exception: "{part}". Use box:count (e.g. 5:30).')

    if errors:
        return render(request, 'inventory/add_shipment.html', {
            'errors': errors,
            'form_data': form_data,
        })

    # Create items
    base_url = os.environ.get("SITE_URL", "https://web-production-57c20.up.railway.app")
    created_items = []
    shipment_key = str(uuid.uuid4())[:8]

    for box_num in range(1, num_boxes_int + 1):
        box_content = count_exceptions.get(box_num, items_per_box_int)
        # If specific damaged boxes were listed, only those are damaged.
        # Otherwise fall back to the global "Damage Reported?" flag.
        if damaged_box_set:
            box_damaged = box_num in damaged_box_set
        else:
            box_damaged = damaged == 'yes'

        barcode_payload = f"MFR={manufacturer} | PALLET={pallet_id} | BOX={box_num}"
        encoded_payload = urllib.parse.quote(barcode_payload)
        scanner_url = f"{base_url}/scan/?data={encoded_payload}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(scanner_url)}"

        # Check if item already exists (update it if so)
        existing = InventoryItem.objects.filter(
            manufacturer=manufacturer,
            pallet_id=pallet_id,
            box_id=box_num
        ).first()

        if existing:
            existing.content = box_content
            existing.damaged = box_damaged
            existing.location = location
            existing.description = description
            existing.project_number = project_number
            existing.barcode_payload = barcode_payload
            existing.qr_url = qr_url
            existing.save()
            created_items.append(existing)
        else:
            item = InventoryItem.objects.create(
                manufacturer=manufacturer,
                pallet_id=pallet_id,
                box_id=box_num,
                project_number=project_number,
                content=box_content,
                damaged=box_damaged,
                location=location,
                description=description,
                status='checked_in',
                barcode_payload=barcode_payload,
                qr_url=qr_url,
            )
            created_items.append(item)

    # Store the shipment key in the session for downloads
    request.session[f'shipment_{shipment_key}'] = [item.id for item in created_items]

    return render(request, 'inventory/shipment_result.html', {
        'items': created_items,
        'manufacturer': manufacturer,
        'pallet_id': pallet_id,
        'shipment_key': shipment_key,
    })


def download_shipment_excel(request, shipment_key):
    """Download shipment items as Excel file for QR code printer"""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    item_ids = request.session.get(f'shipment_{shipment_key}', [])
    if not item_ids:
        return HttpResponse('Shipment not found or session expired.', status=404)

    items = InventoryItem.objects.filter(id__in=item_ids).order_by('box_id')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Shipment Items'

    # Header styling
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='8B1A1A', end_color='8B1A1A', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    headers = ['Box ID', 'Manufacturer', 'Pallet ID', 'Contents (Qty)', 'Damaged',
               'Location', 'Description', 'Barcode Payload', 'Scanner URL', 'QR Code URL']

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    # Data rows
    for row_num, item in enumerate(items, 2):
        base_url = os.environ.get("SITE_URL", "https://web-production-57c20.up.railway.app")
        encoded_payload = urllib.parse.quote(item.barcode_payload)
        scanner_url = f"{base_url}/scan/?data={encoded_payload}"

        row_data = [
            item.box_id,
            item.manufacturer,
            item.pallet_id,
            item.content,
            'Yes' if item.damaged else 'No',
            item.location,
            item.description,
            item.barcode_payload,
            scanner_url,
            item.qr_url,
        ]

        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num, value=value)
            cell.border = thin_border

    # Auto-fit column widths
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_length + 2, 50)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    first_item = items.first()
    if first_item:
        filename = f"shipment_{first_item.manufacturer}_{first_item.pallet_id}.xlsx"
    else:
        filename = "shipment_items.xlsx"
    filename = filename.replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@csrf_exempt
@require_http_methods(["POST"])
def edit_item(request):
    """Edit individual item fields (content, damaged, location, description)"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        item = get_object_or_404(InventoryItem, id=item_id)

        if 'content' in data:
            item.content = int(data['content'])
        if 'damaged' in data:
            item.damaged = data['damaged']
        if 'location' in data:
            item.location = data['location']
        if 'description' in data:
            item.description = data['description']
        if 'project_number' in data:
            item.project_number = data['project_number']

        item.save()

        return JsonResponse({
            'success': True,
            'content': item.content,
            'damaged': item.damaged,
            'location': item.location,
            'description': item.description,
            'project_number': item.project_number,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def download_shipment_csv(request, shipment_key):
    """Download shipment items as CSV file"""
    item_ids = request.session.get(f'shipment_{shipment_key}', [])
    if not item_ids:
        return HttpResponse('Shipment not found or session expired.', status=404)

    items = InventoryItem.objects.filter(id__in=item_ids).order_by('box_id')

    first_item = items.first()
    if first_item:
        filename = f"shipment_{first_item.manufacturer}_{first_item.pallet_id}.csv"
    else:
        filename = "shipment_items.csv"
    filename = filename.replace(' ', '_')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Box ID', 'Manufacturer', 'Pallet ID', 'Contents (Qty)', 'Damaged',
                     'Location', 'Description', 'Barcode Payload', 'Scanner URL', 'QR Code URL'])

    base_url = os.environ.get("SITE_URL", "https://web-production-57c20.up.railway.app")

    for item in items:
        encoded_payload = urllib.parse.quote(item.barcode_payload)
        scanner_url = f"{base_url}/scan/?data={encoded_payload}"
        writer.writerow([
            item.box_id,
            item.manufacturer,
            item.pallet_id,
            item.content,
            'Yes' if item.damaged else 'No',
            item.location,
            item.description,
            item.barcode_payload,
            scanner_url,
            item.qr_url,
        ])

    return response
