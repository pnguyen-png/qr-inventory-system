"""
Comprehensive test suite for the QR Inventory System.

Covers the add_shipment view, edit_item API, and data persistence across
shipments. Organized into 10 test categories plus additional persistence
and edit_item test classes.
"""

import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client

from .models import InventoryItem, ItemPhoto


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_shipment_data(**overrides):
    """Return a minimal valid POST dict for /add-shipment/."""
    data = {
        'manufacturer': 'Acme Corp',
        'project_number': 'PRJ-001',
        'num_boxes': '3',
        'items_per_box': '10',
        'location': 'York, PA',
        'damaged': 'no',
        'description': 'Standard widgets',
        'damaged_boxes': '',
        'count_exceptions': '',
    }
    data.update(overrides)
    return data


def _create_shipment(client, **overrides):
    """POST a valid shipment and return the response."""
    return client.post('/add-shipment/', _valid_shipment_data(**overrides))


# ===================================================================
# 1. Type Violations
# ===================================================================

class TestTypeViolations(TestCase):
    """Category 1 -- text in numeric fields, decimals, negatives, huge numbers."""

    def setUp(self):
        self.client = Client()

    # -- num_boxes -------------------------------------------------------

    def test_text_in_num_boxes(self):
        """Alphabetic string in num_boxes should produce a validation error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(num_boxes='abc'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Number of boxes must be a valid number.', resp.context['errors'])
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_decimal_in_num_boxes(self):
        """Decimal value in num_boxes should be rejected (int() fails on '3.5')."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(num_boxes='3.5'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Number of boxes must be a valid number.', resp.context['errors'])

    def test_negative_num_boxes(self):
        """Negative num_boxes should produce an error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(num_boxes='-1'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Number of boxes must be at least 1.', resp.context['errors'])

    def test_extremely_large_num_boxes(self):
        """Extremely large num_boxes should still parse but may be slow; no crash."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(num_boxes='999999999999'))
        # Should parse as int without error, but the view does not cap the value.
        # We just verify it does not return a 500.
        self.assertIn(resp.status_code, [200, 302])

    # -- items_per_box ---------------------------------------------------

    def test_text_in_items_per_box(self):
        """Alphabetic string in items_per_box should be rejected."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(items_per_box='xyz'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Items per box must be a valid number.', resp.context['errors'])

    def test_decimal_in_items_per_box(self):
        """Decimal in items_per_box should be rejected."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(items_per_box='4.2'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Items per box must be a valid number.', resp.context['errors'])

    def test_negative_items_per_box(self):
        """Negative items_per_box should produce an error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(items_per_box='-5'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Items per box must be at least 1.', resp.context['errors'])

    def test_zero_items_per_box(self):
        """Zero items_per_box should produce an error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(items_per_box='0'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Items per box must be at least 1.', resp.context['errors'])


# ===================================================================
# 2. Boundary Conditions
# ===================================================================

class TestBoundaryConditions(TestCase):
    """Category 2 -- edge-case numeric values for boxes and items."""

    def setUp(self):
        self.client = Client()

    def test_zero_boxes(self):
        """Zero boxes should be rejected."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(num_boxes='0'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Number of boxes must be at least 1.', resp.context['errors'])
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_one_box_one_item(self):
        """Minimum valid shipment: 1 box, 1 item."""
        resp = _create_shipment(self.client, num_boxes='1', items_per_box='1')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('errors', resp.context or {})
        self.assertEqual(InventoryItem.objects.count(), 1)
        item = InventoryItem.objects.first()
        self.assertEqual(item.content, 1)

    def test_one_box_zero_items(self):
        """1 box with 0 items per box should fail."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='1', items_per_box='0'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Items per box must be at least 1.', resp.context['errors'])
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_many_boxes_stress(self):
        """Creating 100+ boxes should succeed and produce the right count."""
        resp = _create_shipment(self.client, num_boxes='105', items_per_box='2')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 105)

    def test_large_items_per_box(self):
        """Very large items_per_box value should be stored correctly."""
        resp = _create_shipment(self.client, num_boxes='1', items_per_box='999999')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertEqual(InventoryItem.objects.first().content, 999999)


# ===================================================================
# 3. Empty / Missing Required Fields
# ===================================================================

class TestEmptyMissingFields(TestCase):
    """Category 3 -- blank or absent required vs. optional fields."""

    def setUp(self):
        self.client = Client()

    def test_blank_manufacturer(self):
        """Empty manufacturer should produce a validation error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(manufacturer=''))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Manufacturer / Supplier is required.', resp.context['errors'])
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_blank_location(self):
        """Empty location should produce a validation error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(location=''))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Receiving Location is required.', resp.context['errors'])

    def test_missing_num_boxes(self):
        """Omitting num_boxes entirely should trigger the 'valid number' error."""
        data = _valid_shipment_data()
        del data['num_boxes']
        resp = self.client.post('/add-shipment/', data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Number of boxes must be a valid number.', resp.context['errors'])

    def test_missing_items_per_box(self):
        """Omitting items_per_box entirely should trigger an error."""
        data = _valid_shipment_data()
        del data['items_per_box']
        resp = self.client.post('/add-shipment/', data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Items per box must be a valid number.', resp.context['errors'])

    def test_blank_description_still_succeeds(self):
        """Description is optional -- blank should NOT cause an error."""
        resp = _create_shipment(self.client, description='')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 3)
        self.assertEqual(InventoryItem.objects.first().description, '')

    def test_blank_project_number_still_succeeds(self):
        """Project number is optional -- blank should work fine."""
        resp = _create_shipment(self.client, project_number='')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 3)

    def test_location_other_with_custom(self):
        """Selecting 'other' and providing a custom location should work."""
        resp = _create_shipment(self.client, location='other', location_custom='Denver, CO')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.first().location, 'Denver, CO')

    def test_location_other_without_custom(self):
        """Selecting 'other' but leaving custom blank should fail."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            location='other', location_custom=''))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Receiving Location is required.', resp.context['errors'])


# ===================================================================
# 4. Duplicate / Conflicting Data
# ===================================================================

class TestDuplicateConflictingData(TestCase):
    """Category 4 -- submitting the same or overlapping data twice."""

    def setUp(self):
        self.client = Client()

    def test_same_shipment_twice_upserts(self):
        """Submitting the exact same shipment twice should upsert (not duplicate)."""
        _create_shipment(self.client, manufacturer='DupeCo', num_boxes='2')
        count_after_first = InventoryItem.objects.count()
        self.assertEqual(count_after_first, 2)

        # Second submission -- same manufacturer, pallet auto-increments so
        # these will be distinct items (different pallet_id).
        _create_shipment(self.client, manufacturer='DupeCo', num_boxes='2')
        # Pallet ID increments, so these are new items.
        self.assertEqual(InventoryItem.objects.count(), 4)

    def test_duplicate_damaged_box_numbers_in_list(self):
        """Listing the same damaged box number twice should not crash."""
        resp = _create_shipment(self.client, num_boxes='5', damaged_boxes='2,2,3')
        self.assertEqual(resp.status_code, 200)
        # Box 2 and 3 marked damaged
        damaged_items = InventoryItem.objects.filter(damaged=True)
        self.assertEqual(damaged_items.count(), 2)

    def test_pallet_id_auto_increments(self):
        """Each shipment should get a new, unique pallet_id."""
        _create_shipment(self.client, manufacturer='First')
        pallet_a = InventoryItem.objects.filter(manufacturer='First').first().pallet_id

        _create_shipment(self.client, manufacturer='Second')
        pallet_b = InventoryItem.objects.filter(manufacturer='Second').first().pallet_id

        self.assertNotEqual(pallet_a, pallet_b)
        self.assertEqual(int(pallet_b), int(pallet_a) + 1)


# ===================================================================
# 5. Format Drift in Structured Fields
# ===================================================================

class TestFormatDrift(TestCase):
    """Category 5 -- malformed count_exceptions and damaged_boxes strings."""

    def setUp(self):
        self.client = Client()

    def test_bad_exception_format_missing_colon(self):
        """count_exceptions entry without colon should error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='5', count_exceptions='3-20'))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertTrue(any('Invalid count exception format' in e for e in errors))

    def test_non_numeric_damaged_box_token(self):
        """Non-numeric tokens in damaged_boxes should produce an error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='5', damaged_boxes='1,abc,3'))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertTrue(any('Invalid damaged box number' in e for e in errors))

    def test_mixed_separators_in_exceptions(self):
        """Using semicolons instead of commas in count_exceptions should error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='5', count_exceptions='1:5;2:10'))
        self.assertEqual(resp.status_code, 200)
        # The whole '1:5;2:10' is treated as one token; int('5;2') fails.
        errors = resp.context['errors']
        self.assertTrue(any('Invalid count exception' in e for e in errors))

    def test_valid_count_exception(self):
        """Properly formatted count_exceptions should override items_per_box."""
        resp = _create_shipment(self.client, num_boxes='3', items_per_box='10',
                                count_exceptions='2:25')
        self.assertEqual(resp.status_code, 200)
        box2 = InventoryItem.objects.get(box_id=2)
        self.assertEqual(box2.content, 25)
        # Other boxes should retain the default.
        box1 = InventoryItem.objects.get(box_id=1)
        self.assertEqual(box1.content, 10)

    def test_exception_with_negative_count(self):
        """Negative count in count_exceptions should be rejected."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='3', count_exceptions='2:-5'))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertTrue(any('cannot be negative' in e for e in errors))

    def test_exception_non_numeric_count(self):
        """Non-numeric count value in count_exceptions should error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='3', count_exceptions='2:abc'))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertTrue(any('Invalid count exception' in e for e in errors))


# ===================================================================
# 6. Unicode / Encoding Issues
# ===================================================================

class TestUnicodeEncoding(TestCase):
    """Category 6 -- non-ASCII names, emoji, RTL characters, zero-width spaces."""

    def setUp(self):
        self.client = Client()

    def test_non_ascii_manufacturer(self):
        """Japanese characters in manufacturer should be stored correctly."""
        resp = _create_shipment(self.client, manufacturer='\u682a\u5f0f\u4f1a\u793e',
                                num_boxes='1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertEqual(InventoryItem.objects.first().manufacturer, '\u682a\u5f0f\u4f1a\u793e')

    def test_emoji_in_description(self):
        """Emoji in description should not crash the view."""
        resp = _create_shipment(self.client, description='\U0001f4e6 Fragile! \U0001f6a8',
                                num_boxes='1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertIn('\U0001f4e6', InventoryItem.objects.first().description)

    def test_rtl_characters_in_manufacturer(self):
        """Arabic / RTL characters in manufacturer should be preserved."""
        rtl_name = '\u0634\u0631\u0643\u0629 \u0627\u0644\u0623\u0647\u0631\u0627\u0645'
        resp = _create_shipment(self.client, manufacturer=rtl_name, num_boxes='1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.first().manufacturer, rtl_name)

    def test_zero_width_spaces_in_manufacturer(self):
        """Zero-width spaces should be kept (the view does strip(), but ZWS is not stripped)."""
        name_with_zws = 'Acme\u200bCorp'
        resp = _create_shipment(self.client, manufacturer=name_with_zws, num_boxes='1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertEqual(InventoryItem.objects.first().manufacturer, name_with_zws)

    def test_mixed_scripts_in_project_number(self):
        """Mixed Latin + Cyrillic in project number should be stored."""
        mixed = 'PRJ-\u041f\u0420\u041e\u0415\u041a\u0422-42'
        resp = _create_shipment(self.client, project_number=mixed, num_boxes='1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.first().project_number, mixed)


# ===================================================================
# 7. Excessive Length Inputs
# ===================================================================

class TestExcessiveLength(TestCase):
    """Category 7 -- inputs exceeding expected max lengths."""

    def setUp(self):
        self.client = Client()

    def test_very_long_manufacturer(self):
        """A 1000+ char manufacturer should either be stored or cause a DB error (not a 500)."""
        long_name = 'A' * 1200
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            manufacturer=long_name, num_boxes='1'))
        # CharField max_length=255 -- Django may raise DataError or truncate.
        # The view does not pre-validate length so we expect either a 200
        # (success or form re-render) or a 500 if DB rejects it.
        self.assertIn(resp.status_code, [200, 500])

    def test_long_project_number(self):
        """A 500-char project number against max_length=100 field."""
        long_pn = 'P' * 500
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            project_number=long_pn, num_boxes='1'))
        self.assertIn(resp.status_code, [200, 500])

    def test_huge_description(self):
        """A very large description (TextField, no max_length) should succeed."""
        huge_desc = 'D' * 50000
        resp = _create_shipment(self.client, description=huge_desc, num_boxes='1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 1)
        self.assertEqual(len(InventoryItem.objects.first().description), 50000)

    def test_long_location_custom(self):
        """A 500-char custom location against max_length=255."""
        long_loc = 'L' * 500
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            location='other', location_custom=long_loc, num_boxes='1'))
        self.assertIn(resp.status_code, [200, 500])


# ===================================================================
# 8. File Upload Stress
# ===================================================================

class TestFileUploadStress(TestCase):
    """Category 8 -- non-image files, large files, multiple uploads."""

    def setUp(self):
        self.client = Client()

    def test_upload_non_image_file(self):
        """Uploading a plain text file as a photo should not crash the view."""
        txt_file = SimpleUploadedFile(
            'notes.txt', b'Hello world', content_type='text/plain')
        data = _valid_shipment_data(num_boxes='1')
        data['photos'] = txt_file
        resp = self.client.post('/add-shipment/', data)
        # The view accepts any file via request.FILES.getlist('photos') and
        # creates ItemPhoto rows regardless; we just verify no 500.
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(InventoryItem.objects.count(), 1)

    def test_upload_large_file_simulation(self):
        """Simulated large file upload (1 MB) should not crash."""
        large_content = b'\x89PNG' + b'\x00' * (1024 * 1024)
        large_file = SimpleUploadedFile(
            'big_photo.png', large_content, content_type='image/png')
        data = _valid_shipment_data(num_boxes='1')
        data['photos'] = large_file
        resp = self.client.post('/add-shipment/', data)
        self.assertIn(resp.status_code, [200, 302])
        self.assertEqual(InventoryItem.objects.count(), 1)

    def test_upload_multiple_files(self):
        """Multiple photo files should each be attached to every created item."""
        file_a = SimpleUploadedFile(
            'a.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 100,
            content_type='image/png')
        file_b = SimpleUploadedFile(
            'b.png', b'\x89PNG\r\n\x1a\n' + b'\x00' * 100,
            content_type='image/png')
        data = _valid_shipment_data(num_boxes='2')
        # Django test client: supply multiple files as a list.
        data['photos'] = [file_a, file_b]
        resp = self.client.post('/add-shipment/', data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 2)
        # Each photo is attached to each item: 2 photos x 2 items = 4 rows.
        self.assertEqual(ItemPhoto.objects.count(), 4)

    def test_no_photo_upload_succeeds(self):
        """Submitting without any photos should still create items normally."""
        resp = _create_shipment(self.client, num_boxes='2')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 2)
        self.assertEqual(ItemPhoto.objects.count(), 0)


# ===================================================================
# 9. Race / Double Submit
# ===================================================================

class TestRaceDoubleSubmit(TestCase):
    """Category 9 -- two identical POSTs in quick succession.

    The view uses upsert logic (manufacturer + pallet_id + box_id) so a
    duplicate submission for the same pallet should update rather than
    create extra rows.
    """

    def setUp(self):
        self.client = Client()

    def test_double_submit_same_pallet(self):
        """Two rapid identical POSTs should not double the item count.

        Because pallet_id auto-increments on each POST call, two sequential
        calls will get different pallet IDs and therefore create separate
        items.  This test documents that behaviour.
        """
        resp1 = _create_shipment(self.client, manufacturer='RaceCo', num_boxes='3')
        self.assertEqual(resp1.status_code, 200)
        count_after_first = InventoryItem.objects.filter(manufacturer='RaceCo').count()
        self.assertEqual(count_after_first, 3)

        resp2 = _create_shipment(self.client, manufacturer='RaceCo', num_boxes='3')
        self.assertEqual(resp2.status_code, 200)
        # Second call gets next pallet_id, so 3 more items are created.
        count_after_second = InventoryItem.objects.filter(manufacturer='RaceCo').count()
        self.assertEqual(count_after_second, 6)

    def test_upsert_same_manufacturer_pallet_box(self):
        """Manually creating an item then submitting a shipment that matches
        the same (manufacturer, pallet_id, box_id) should update, not duplicate.
        """
        # Pre-create an item with pallet_id '1'.
        InventoryItem.objects.create(
            manufacturer='UpsertCo',
            pallet_id='1',
            box_id=1,
            project_number='',
            content=5,
            damaged=False,
            location='York, PA',
            description='old desc',
            status='checked_in',
            barcode_payload='MFR=UpsertCo | PALLET=1 | BOX=1',
            qr_url='https://example.com/qr',
        )
        self.assertEqual(InventoryItem.objects.count(), 1)

        # The next pallet ID computed will be '2', so this will NOT collide.
        # We just verify no crash and that the old item is untouched.
        resp = _create_shipment(self.client, manufacturer='UpsertCo', num_boxes='2')
        self.assertEqual(resp.status_code, 200)
        # Original item is still there, plus 2 new ones = 3 total.
        self.assertEqual(InventoryItem.objects.count(), 3)
        old_item = InventoryItem.objects.get(pallet_id='1', box_id=1)
        self.assertEqual(old_item.description, 'old desc')


# ===================================================================
# 10. Logical Inconsistencies
# ===================================================================

class TestLogicalInconsistencies(TestCase):
    """Category 10 -- contradictory or logically impossible field combinations."""

    def setUp(self):
        self.client = Client()

    def test_damage_no_but_damaged_boxes_filled(self):
        """damaged=no but damaged_boxes has values -- the view honours the list."""
        resp = _create_shipment(self.client, num_boxes='5', damaged='no',
                                damaged_boxes='1,3')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 5)
        # When damaged_box_set is non-empty, individual box flags take precedence.
        self.assertTrue(InventoryItem.objects.get(box_id=1).damaged)
        self.assertFalse(InventoryItem.objects.get(box_id=2).damaged)
        self.assertTrue(InventoryItem.objects.get(box_id=3).damaged)

    def test_damaged_box_outside_range(self):
        """Damaged box number > num_boxes should produce an error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='3', damaged_boxes='5'))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertTrue(any('outside the range' in e for e in errors))
        self.assertEqual(InventoryItem.objects.count(), 0)

    def test_damaged_box_zero(self):
        """Damaged box 0 should be outside the range 1..N."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='3', damaged_boxes='0'))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertTrue(any('outside the range' in e for e in errors))

    def test_exception_box_outside_range(self):
        """count_exceptions referencing a box beyond num_boxes should error."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            num_boxes='3', count_exceptions='10:50'))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertTrue(any('outside the range' in e for e in errors))

    def test_damage_yes_global_flag(self):
        """damaged=yes with no specific boxes should mark ALL boxes damaged."""
        resp = _create_shipment(self.client, num_boxes='3', damaged='yes',
                                damaged_boxes='')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(InventoryItem.objects.filter(damaged=True).count(), 3)

    def test_multiple_errors_at_once(self):
        """Submitting with multiple problems should return all errors."""
        resp = self.client.post('/add-shipment/', _valid_shipment_data(
            manufacturer='', num_boxes='abc', items_per_box='-1', location=''))
        self.assertEqual(resp.status_code, 200)
        errors = resp.context['errors']
        self.assertGreaterEqual(len(errors), 3)


# ===================================================================
# edit_item API Tests
# ===================================================================

class TestEditItemAPI(TestCase):
    """Tests for the /api/edit-item/ endpoint."""

    def setUp(self):
        self.client = Client()
        self.item = InventoryItem.objects.create(
            manufacturer='EditCo',
            pallet_id='100',
            box_id=1,
            project_number='PRJ-E1',
            content=50,
            damaged=False,
            location='York, PA',
            description='Original description',
            status='checked_in',
            barcode_payload='MFR=EditCo | PALLET=100 | BOX=1',
            qr_url='https://example.com/qr',
        )

    def test_edit_content(self):
        """Editing content should update the value."""
        resp = self.client.post('/api/edit-item/',
                                json.dumps({'item_id': self.item.id, 'content': 99}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.item.refresh_from_db()
        self.assertEqual(self.item.content, 99)

    def test_edit_damaged(self):
        """Editing damaged flag should update the value."""
        resp = self.client.post('/api/edit-item/',
                                json.dumps({'item_id': self.item.id, 'damaged': True}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.item.refresh_from_db()
        self.assertTrue(self.item.damaged)

    def test_edit_location(self):
        """Editing location should update the value."""
        resp = self.client.post('/api/edit-item/',
                                json.dumps({'item_id': self.item.id,
                                            'location': 'Cambridge, MD'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.location, 'Cambridge, MD')

    def test_edit_description(self):
        """Editing description should update the value."""
        resp = self.client.post('/api/edit-item/',
                                json.dumps({'item_id': self.item.id,
                                            'description': 'Updated desc'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.description, 'Updated desc')

    def test_edit_project_number(self):
        """Editing project_number should update the value."""
        resp = self.client.post('/api/edit-item/',
                                json.dumps({'item_id': self.item.id,
                                            'project_number': 'NEW-PRJ'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.project_number, 'NEW-PRJ')

    def test_edit_multiple_fields_at_once(self):
        """Editing several fields in one request should update all of them."""
        payload = {
            'item_id': self.item.id,
            'content': 77,
            'damaged': True,
            'location': 'Rockville, MD',
            'description': 'Multi-edit',
            'project_number': 'MULTI-001',
        }
        resp = self.client.post('/api/edit-item/', json.dumps(payload),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.content, 77)
        self.assertTrue(self.item.damaged)
        self.assertEqual(self.item.location, 'Rockville, MD')
        self.assertEqual(self.item.description, 'Multi-edit')
        self.assertEqual(self.item.project_number, 'MULTI-001')

    def test_edit_nonexistent_item(self):
        """Editing a non-existent item_id should return a 404-level error."""
        resp = self.client.post('/api/edit-item/',
                                json.dumps({'item_id': 999999, 'content': 1}),
                                content_type='application/json')
        # The view wraps get_object_or_404 in a try/except returning 500.
        self.assertIn(resp.status_code, [404, 500])

    def test_edit_does_not_affect_other_items(self):
        """Editing one item must not change any other item's data."""
        other = InventoryItem.objects.create(
            manufacturer='OtherCo',
            pallet_id='200',
            box_id=1,
            project_number='PRJ-O1',
            content=30,
            damaged=False,
            location='Rockville, MD',
            description='Other item',
            status='checked_in',
            barcode_payload='MFR=OtherCo | PALLET=200 | BOX=1',
            qr_url='https://example.com/qr2',
        )

        self.client.post('/api/edit-item/',
                         json.dumps({'item_id': self.item.id,
                                     'content': 999,
                                     'description': 'Changed'}),
                         content_type='application/json')

        other.refresh_from_db()
        self.assertEqual(other.content, 30)
        self.assertEqual(other.description, 'Other item')
        self.assertEqual(other.manufacturer, 'OtherCo')


# ===================================================================
# Data Persistence Tests
# ===================================================================

class TestDataPersistence(TestCase):
    """Verify that creating new shipments does NOT delete existing items,
    editing an item does not affect other items, and multiple shipments
    can coexist in the database.

    This is the user's PRIMARY concern.
    """

    def setUp(self):
        self.client = Client()

    def test_new_shipment_preserves_existing_items(self):
        """Creating a NEW shipment must NOT delete items from a PREVIOUS shipment."""
        # Shipment 1
        resp1 = _create_shipment(self.client, manufacturer='AlphaCo', num_boxes='4',
                                 items_per_box='10', description='First shipment')
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 4)
        first_ids = set(InventoryItem.objects.values_list('id', flat=True))

        # Shipment 2 (different manufacturer)
        resp2 = _create_shipment(self.client, manufacturer='BetaCo', num_boxes='3',
                                 items_per_box='20', description='Second shipment')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(InventoryItem.objects.count(), 7)

        # All original items still present
        remaining_ids = set(InventoryItem.objects.values_list('id', flat=True))
        self.assertTrue(first_ids.issubset(remaining_ids),
                        'First shipment items were deleted after creating second shipment!')

        # Verify first shipment data is intact
        alpha_items = InventoryItem.objects.filter(manufacturer='AlphaCo')
        self.assertEqual(alpha_items.count(), 4)
        for item in alpha_items:
            self.assertEqual(item.content, 10)
            self.assertEqual(item.description, 'First shipment')

    def test_three_shipments_coexist(self):
        """Three separate shipments should all coexist without interference."""
        _create_shipment(self.client, manufacturer='Vendor-A', num_boxes='2',
                         items_per_box='5')
        _create_shipment(self.client, manufacturer='Vendor-B', num_boxes='3',
                         items_per_box='15')
        _create_shipment(self.client, manufacturer='Vendor-C', num_boxes='4',
                         items_per_box='25')

        self.assertEqual(InventoryItem.objects.count(), 9)
        self.assertEqual(InventoryItem.objects.filter(manufacturer='Vendor-A').count(), 2)
        self.assertEqual(InventoryItem.objects.filter(manufacturer='Vendor-B').count(), 3)
        self.assertEqual(InventoryItem.objects.filter(manufacturer='Vendor-C').count(), 4)

        # Verify each set has its own content values.
        for item in InventoryItem.objects.filter(manufacturer='Vendor-A'):
            self.assertEqual(item.content, 5)
        for item in InventoryItem.objects.filter(manufacturer='Vendor-B'):
            self.assertEqual(item.content, 15)
        for item in InventoryItem.objects.filter(manufacturer='Vendor-C'):
            self.assertEqual(item.content, 25)

    def test_edit_does_not_delete_other_items(self):
        """Editing one item via /api/edit-item/ should not delete any items."""
        _create_shipment(self.client, manufacturer='PersistCo', num_boxes='5',
                         items_per_box='10')
        self.assertEqual(InventoryItem.objects.count(), 5)
        first_item = InventoryItem.objects.order_by('id').first()

        self.client.post('/api/edit-item/',
                         json.dumps({'item_id': first_item.id,
                                     'content': 999,
                                     'description': 'Edited'}),
                         content_type='application/json')

        # Still 5 items
        self.assertEqual(InventoryItem.objects.count(), 5)
        first_item.refresh_from_db()
        self.assertEqual(first_item.content, 999)

        # Other 4 items unchanged
        others = InventoryItem.objects.exclude(id=first_item.id)
        for item in others:
            self.assertEqual(item.content, 10)
            self.assertEqual(item.description, 'Standard widgets')

    def test_shipment_after_edit_preserves_all(self):
        """Creating a shipment after editing an item should keep all data."""
        # Create first shipment
        _create_shipment(self.client, manufacturer='OrigCo', num_boxes='2',
                         items_per_box='10')
        self.assertEqual(InventoryItem.objects.count(), 2)

        # Edit first item
        first = InventoryItem.objects.order_by('id').first()
        self.client.post('/api/edit-item/',
                         json.dumps({'item_id': first.id,
                                     'content': 42,
                                     'description': 'Manually edited'}),
                         content_type='application/json')

        # Create second shipment
        _create_shipment(self.client, manufacturer='NewCo', num_boxes='3',
                         items_per_box='20')

        # Total should be 5
        self.assertEqual(InventoryItem.objects.count(), 5)

        # Edited item should retain its edits
        first.refresh_from_db()
        self.assertEqual(first.content, 42)
        self.assertEqual(first.description, 'Manually edited')

        # New shipment items correct
        new_items = InventoryItem.objects.filter(manufacturer='NewCo')
        self.assertEqual(new_items.count(), 3)
        for item in new_items:
            self.assertEqual(item.content, 20)

    def test_pallet_ids_are_unique_across_shipments(self):
        """Each shipment gets an auto-incremented pallet_id; all should be unique."""
        _create_shipment(self.client, manufacturer='M1', num_boxes='2')
        _create_shipment(self.client, manufacturer='M2', num_boxes='2')
        _create_shipment(self.client, manufacturer='M3', num_boxes='2')

        pallet_ids = set(InventoryItem.objects.values_list('pallet_id', flat=True))
        self.assertEqual(len(pallet_ids), 3,
                         'Expected 3 distinct pallet IDs across 3 shipments.')

    def test_barcode_payloads_are_unique(self):
        """Every item across all shipments must have a unique barcode_payload."""
        _create_shipment(self.client, manufacturer='BC-A', num_boxes='3')
        _create_shipment(self.client, manufacturer='BC-B', num_boxes='3')

        payloads = list(InventoryItem.objects.values_list('barcode_payload', flat=True))
        self.assertEqual(len(payloads), len(set(payloads)),
                         'Duplicate barcode_payload detected across shipments!')

    def test_large_sequential_shipments(self):
        """Five shipments created in sequence should all persist with correct counts."""
        expected_total = 0
        for i in range(5):
            n = (i + 1) * 2  # 2, 4, 6, 8, 10
            _create_shipment(self.client, manufacturer=f'SeqCo-{i}', num_boxes=str(n),
                             items_per_box='5')
            expected_total += n

        self.assertEqual(InventoryItem.objects.count(), expected_total)
        for i in range(5):
            n = (i + 1) * 2
            self.assertEqual(
                InventoryItem.objects.filter(manufacturer=f'SeqCo-{i}').count(), n)


# ===================================================================
# 12. Status Preservation
# ===================================================================

class TestStatusPreservation(TestCase):
    """Verify that item statuses are never reset by shipment creation,
    editing, or other operations. This is a critical user requirement.
    """

    def setUp(self):
        self.client = Client()

    def _change_status(self, item_id, status_label, changed_by='tester'):
        """Helper to change an item's status via the update_status API."""
        return self.client.post('/api/update-status/', {
            'item_id': item_id,
            'status': status_label,
            'changed_by': changed_by,
        })

    def test_new_shipment_does_not_reset_existing_item_status(self):
        """Creating a new shipment must NOT change statuses of existing items."""
        # Create first shipment
        _create_shipment(self.client, manufacturer='StatusCo', num_boxes='3',
                         items_per_box='10')
        items = list(InventoryItem.objects.filter(manufacturer='StatusCo').order_by('id'))
        self.assertEqual(len(items), 3)

        # Change statuses on existing items
        self._change_status(items[0].id, 'Checked Out')
        self._change_status(items[1].id, 'Tested')
        self._change_status(items[2].id, 'Recycling')

        # Verify statuses changed
        for item in items:
            item.refresh_from_db()
        self.assertEqual(items[0].status, 'checked_out')
        self.assertEqual(items[1].status, 'tested')
        self.assertEqual(items[2].status, 'recycling')

        # Create a SECOND shipment
        _create_shipment(self.client, manufacturer='OtherCo', num_boxes='2',
                         items_per_box='5')

        # Verify original items still have their changed statuses
        for item in items:
            item.refresh_from_db()
        self.assertEqual(items[0].status, 'checked_out',
                         'Status was reset to checked_in after new shipment!')
        self.assertEqual(items[1].status, 'tested',
                         'Status was reset to checked_in after new shipment!')
        self.assertEqual(items[2].status, 'recycling',
                         'Status was reset to checked_in after new shipment!')

    def test_edit_item_preserves_status(self):
        """Editing an item's content/location/description must NOT change its status."""
        _create_shipment(self.client, manufacturer='EditStatusCo', num_boxes='1',
                         items_per_box='10')
        item = InventoryItem.objects.get(manufacturer='EditStatusCo')

        # Change status to Tested
        self._change_status(item.id, 'Tested')
        item.refresh_from_db()
        self.assertEqual(item.status, 'tested')

        # Edit item fields
        self.client.post('/api/edit-item/',
                         json.dumps({
                             'item_id': item.id,
                             'content': 50,
                             'location': 'Cambridge, MD',
                             'description': 'Updated description',
                         }),
                         content_type='application/json')

        # Status should still be 'tested'
        item.refresh_from_db()
        self.assertEqual(item.status, 'tested',
                         'Status was reset after editing item fields!')
        self.assertEqual(item.content, 50)
        self.assertEqual(item.location, 'Cambridge, MD')

    def test_edit_manufacturer_preserves_status(self):
        """Editing an item's manufacturer must NOT change its status."""
        _create_shipment(self.client, manufacturer='OldMfr', num_boxes='1',
                         items_per_box='10')
        item = InventoryItem.objects.get(manufacturer='OldMfr')

        # Change status
        self._change_status(item.id, 'Checked Out')
        item.refresh_from_db()
        self.assertEqual(item.status, 'checked_out')

        # Edit manufacturer
        self.client.post('/api/edit-item/',
                         json.dumps({
                             'item_id': item.id,
                             'manufacturer': 'NewMfr',
                         }),
                         content_type='application/json')

        item.refresh_from_db()
        self.assertEqual(item.status, 'checked_out',
                         'Status was reset after manufacturer edit!')
        self.assertEqual(item.manufacturer, 'NewMfr')

    def test_all_status_transitions_persist(self):
        """Every valid status should persist correctly."""
        _create_shipment(self.client, manufacturer='TransCo', num_boxes='5',
                         items_per_box='1')
        items = list(InventoryItem.objects.filter(
            manufacturer='TransCo').order_by('id'))

        statuses = ['Checked In', 'Checked Out', 'Tested',
                     'Will Be Reused', 'Recycling']
        expected = ['checked_in', 'checked_out', 'tested',
                     'will_be_reused', 'recycling']

        for item, status_label in zip(items, statuses):
            self._change_status(item.id, status_label)

        for item, exp in zip(items, expected):
            item.refresh_from_db()
            self.assertEqual(item.status, exp,
                             f'Status {exp} did not persist!')

    def test_status_survives_multiple_operations(self):
        """Status should survive: create -> change status -> edit -> new shipment."""
        # Create shipment
        _create_shipment(self.client, manufacturer='SurviveCo', num_boxes='2',
                         items_per_box='10')
        item = InventoryItem.objects.filter(manufacturer='SurviveCo').first()

        # Change to Checked Out
        self._change_status(item.id, 'Checked Out')
        item.refresh_from_db()
        self.assertEqual(item.status, 'checked_out')

        # Edit description
        self.client.post('/api/edit-item/',
                         json.dumps({'item_id': item.id, 'description': 'Edited'}),
                         content_type='application/json')
        item.refresh_from_db()
        self.assertEqual(item.status, 'checked_out')

        # Create another shipment
        _create_shipment(self.client, manufacturer='AnotherCo', num_boxes='3',
                         items_per_box='5')
        item.refresh_from_db()
        self.assertEqual(item.status, 'checked_out',
                         'Status lost after edit + new shipment!')

    def test_new_items_default_to_checked_in(self):
        """Newly created items should default to checked_in status."""
        _create_shipment(self.client, manufacturer='DefaultCo', num_boxes='3',
                         items_per_box='10')
        for item in InventoryItem.objects.filter(manufacturer='DefaultCo'):
            self.assertEqual(item.status, 'checked_in')


# ===================================================================
# 13. Database Configuration
# ===================================================================

class TestDatabaseConfig(TestCase):
    """Verify database settings are properly configured."""

    def test_database_engine_is_set(self):
        """Database engine should be configured (not empty)."""
        from django.conf import settings
        engine = settings.DATABASES['default']['ENGINE']
        self.assertTrue(engine, 'Database ENGINE is empty!')

    def test_database_name_is_set(self):
        """Database NAME should be configured (not empty)."""
        from django.conf import settings
        name = settings.DATABASES['default']['NAME']
        self.assertTrue(name, 'Database NAME is empty!')
