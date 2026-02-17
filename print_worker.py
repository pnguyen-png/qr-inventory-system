#!/usr/bin/env python3
"""
Print Worker for Brother QL-820NWB
===================================
Runs on the local machine connected to the Brother QL printer via USB.
Polls the web app API for pending print jobs, downloads label images,
and sends them to the printer.

Usage:
    python print_worker.py

Environment variables (or edit config below):
    SITE_URL          - Base URL of the web app (e.g. https://web-production-57c20.up.railway.app)
    PRINT_API_SECRET  - Bearer token for authenticating with the print API
    PRINTER_MODEL     - Brother QL model (default: QL-820NWB)
    PRINTER_URI       - USB URI (default: usb://0x04f9:0x209d)
    LABEL_SIZE        - Label size identifier (default: 62)
    POLL_INTERVAL     - Seconds between polls (default: 5)

Requirements (install in a venv):
    pip install requests brother_ql pillow
"""

import os
import sys
import time
import logging
import tempfile
import argparse
from io import BytesIO

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger('print_worker')

# ── Configuration ──────────────────────────────────────────────

SITE_URL = os.environ.get('SITE_URL', 'https://web-production-57c20.up.railway.app')
API_SECRET = os.environ.get('PRINT_API_SECRET', '')
PRINTER_MODEL = os.environ.get('PRINTER_MODEL', 'QL-820NWB')
PRINTER_URI = os.environ.get('PRINTER_URI', 'usb://0x04f9:0x209d')
LABEL_SIZE = os.environ.get('LABEL_SIZE', '62')
POLL_INTERVAL = int(os.environ.get('POLL_INTERVAL', '5'))
BACKEND = os.environ.get('PRINTER_BACKEND', 'pyusb')  # pyusb or linux_kernel


def get_headers():
    return {
        'Authorization': f'Bearer {API_SECRET}',
        'Content-Type': 'application/json',
    }


def fetch_pending_jobs():
    """Fetch list of pending print jobs from the API."""
    url = f'{SITE_URL}/api/print-jobs/pending/'
    try:
        resp = requests.get(url, headers=get_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.error('Failed to fetch pending jobs: %s', e)
        return []


def download_label(image_url):
    """Download label PNG from the API. Returns PIL Image or None."""
    from PIL import Image
    try:
        resp = requests.get(image_url, headers=get_headers(), timeout=30)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        return img
    except Exception as e:
        log.error('Failed to download label from %s: %s', image_url, e)
        return None


def send_to_printer(image):
    """Send a PIL Image to the Brother QL printer. Returns (success, error_msg)."""
    from brother_ql.conversion import convert
    from brother_ql.backends.helpers import send
    from brother_ql.raster import BrotherQLRaster

    try:
        qlr = BrotherQLRaster(PRINTER_MODEL)
        instructions = convert(
            qlr=qlr,
            images=[image],
            label=LABEL_SIZE,
            rotate='auto',
            threshold=70,
            dither=False,
            compress=False,
            red=False,
            dpi_600=False,
            hq=True,
            cut=True,
        )

        log.info('Sending %d bytes to printer at %s ...', len(instructions), PRINTER_URI)
        status = send(
            instructions=instructions,
            printer_identifier=PRINTER_URI,
            backend_identifier=BACKEND,
            blocking=True,
        )

        # brother_ql often reports "printing potentially not successful" even when
        # the print actually worked fine (USB status read timeout). We treat it as
        # success unless we get an explicit error status.
        did_print = status.get('did_print', False)
        outcome = status.get('outcome', 'unknown')

        if did_print:
            log.info('Print confirmed successful.')
            return True, ''

        # Check for real errors vs the common false-negative
        ready = status.get('ready_for_next_job', False)
        errors = [k for k, v in status.items()
                  if k.startswith('error') and v]
        media_error = any(k for k in errors if 'media' in k.lower())

        if errors and media_error:
            err = f'Printer error: {errors}'
            log.error(err)
            return False, err

        # Common case: status read timed out but print likely succeeded
        log.warning(
            'Print status ambiguous (outcome=%s, did_print=%s). '
            'Treating as success — check physical output.',
            outcome, did_print,
        )
        return True, ''

    except Exception as e:
        err = str(e)
        log.error('Print failed: %s', err)
        return False, err


def update_job_status(job_id, status, error=''):
    """Report job status back to the API."""
    url = f'{SITE_URL}/api/print-jobs/{job_id}/update-status/'
    payload = {'status': status}
    if error:
        payload['error'] = error
    try:
        resp = requests.patch(url, json=payload, headers=get_headers(), timeout=15)
        resp.raise_for_status()
        log.info('Job #%d marked as %s', job_id, status)
    except requests.RequestException as e:
        log.error('Failed to update job #%d status: %s', job_id, e)


def process_job(job):
    """Process a single print job: download label, print, update status."""
    job_id = job['id']
    image_url = job['image_url']

    log.info('Processing job #%d ...', job_id)

    image = download_label(image_url)
    if image is None:
        update_job_status(job_id, 'failed', 'Failed to download label image')
        return

    # Verify image dimensions for 62mm label (should be 696px wide)
    w, h = image.size
    if w != 696:
        log.warning('Label image is %dx%d, expected 696px wide for 62mm label. Resizing.', w, h)
        ratio = 696 / w
        image = image.resize((696, int(h * ratio)), resample=3)  # LANCZOS

    success, error = send_to_printer(image)

    if success:
        update_job_status(job_id, 'printed')
    else:
        update_job_status(job_id, 'failed', error)


def run_worker():
    """Main polling loop."""
    log.info('=' * 60)
    log.info('Brother QL Print Worker')
    log.info('  Server:  %s', SITE_URL)
    log.info('  Printer: %s (%s)', PRINTER_MODEL, PRINTER_URI)
    log.info('  Label:   %smm continuous', LABEL_SIZE)
    log.info('  Backend: %s', BACKEND)
    log.info('  Poll:    every %ds', POLL_INTERVAL)
    log.info('=' * 60)

    if not API_SECRET:
        log.error('PRINT_API_SECRET not set. Set it as an environment variable.')
        sys.exit(1)

    consecutive_errors = 0
    while True:
        try:
            jobs = fetch_pending_jobs()
            consecutive_errors = 0

            if jobs:
                log.info('Found %d pending job(s)', len(jobs))
                for job in jobs:
                    process_job(job)
            else:
                log.debug('No pending jobs')

        except KeyboardInterrupt:
            log.info('Worker stopped.')
            break
        except Exception as e:
            consecutive_errors += 1
            backoff = min(30, POLL_INTERVAL * (2 ** consecutive_errors))
            log.error('Unexpected error: %s (retry in %ds)', e, backoff)
            time.sleep(backoff)
            continue

        time.sleep(POLL_INTERVAL)


def print_single_label(item_id):
    """Download and print a single item label directly (bypass job queue)."""
    log.info('Printing label for item #%d ...', item_id)

    url = f'{SITE_URL}/api/items/{item_id}/label.png'
    image = download_label(url)
    if image is None:
        log.error('Could not download label for item #%d', item_id)
        return False

    success, error = send_to_printer(image)
    if success:
        log.info('Label for item #%d printed successfully!', item_id)
    else:
        log.error('Failed to print label for item #%d: %s', item_id, error)
    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Brother QL Print Worker')
    parser.add_argument('--item', type=int, help='Print a single item label by ID (bypass job queue)')
    parser.add_argument('--url', help=f'Server URL (default: {SITE_URL})')
    parser.add_argument('--secret', help='Print API secret (or set PRINT_API_SECRET env var)')
    parser.add_argument('--printer', help=f'Printer URI (default: {PRINTER_URI})')
    parser.add_argument('--backend', choices=['pyusb', 'linux_kernel'], default=BACKEND,
                        help=f'brother_ql backend (default: {BACKEND})')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    if args.url:
        SITE_URL = args.url.rstrip('/')
    if args.secret:
        API_SECRET = args.secret
    if args.printer:
        PRINTER_URI = args.printer
    if args.backend:
        BACKEND = args.backend

    if args.item:
        if not API_SECRET:
            log.error('PRINT_API_SECRET not set.')
            sys.exit(1)
        success = print_single_label(args.item)
        sys.exit(0 if success else 1)
    else:
        run_worker()
