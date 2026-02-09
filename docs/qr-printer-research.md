# QR Code Printer Research for QR Inventory System

## Objective

Find a QR code printer that can be **programmatically triggered** to auto-print when a shipment submission is created/updated in the QR Inventory System (Django 6.0 / Python / PostgreSQL on Railway).

---

## Current System Architecture

The QR Inventory System currently:
- Generates QR codes via the external QRServer API (`api.qrserver.com`)
- Stores QR image URLs in the database (`InventoryItem.qr_url`)
- Exports QR data to Excel/CSV/PDF for **manual printing**
- Has a webhook notification system (`NOTIFICATION_WEBHOOK_URL`) that could be extended for print triggers

**Gap:** No direct printer integration exists today. Users must download Excel files and manually print QR labels.

---

## Recommended Solutions

### Option 1: Zebra Printer + SendFileToPrinter API (Best Overall)

**Hardware:**
| Model | Type | Resolution | Price Range | Best For |
|-------|------|-----------|-------------|----------|
| Zebra ZD421 | Desktop thermal | 203/300 DPI | ~$350-500 | Low-medium volume |
| Zebra ZD621 | Desktop thermal | 203/300 DPI | ~$500-700 | Higher quality labels |
| Zebra ZT411 | Industrial | 203/300/600 DPI | ~$1,500+ | High volume (1000+/day) |

**Integration: SendFileToPrinter REST API**
- **How it works:** Cloud-based REST API — send an HTTPS POST with ZPL commands to print directly to the printer from anywhere. No middleware needed.
- **Protocol:** Simple HTTPS multipart POST request
- **Language agnostic:** Works from Python/Django with `requests` library
- **ZPL support:** Send ZPL templates with variable data (lightweight, fast)
- **Multi-printer:** Can target one or multiple printers per API call
- **Free tier:** 100 API calls/day at no cost; pay-per-call plans available beyond that
- **Developer portal:** Free registration at developer.zebra.com

**Django Integration Example:**
```python
import requests

def print_qr_label(printer_id, manufacturer, pallet_id, box_number, qr_data):
    """Send a ZPL label to a Zebra printer via SendFileToPrinter API."""
    zpl = f"""
    ^XA
    ^FO50,50^A0N,30,30^FD{manufacturer}^FS
    ^FO50,90^A0N,25,25^FDPallet: {pallet_id} | Box: {box_number}^FS
    ^FO50,140^BQN,2,5^FDLA,{qr_data}^FS
    ^XZ
    """
    response = requests.post(
        "https://api.zebra.com/v2/devices/printers/send",
        headers={"apikey": ZEBRA_API_KEY},
        files={"file": ("label.zpl", zpl.encode(), "text/plain")},
        data={"printer_id": printer_id}
    )
    return response.status_code == 200
```

**Pros:**
- Direct cloud-to-printer, no middleware software to install/maintain
- Free tier covers moderate usage
- Industry standard for label printing
- Excellent QR code rendering at 300 DPI
- ZPL templates can be preloaded on the printer for speed

**Cons:**
- Zebra hardware is more expensive than consumer printers
- API is unidirectional (can't confirm print success via API)
- Requires printer to have internet connectivity

---

### Option 2: PrintNode + Any Printer (Most Flexible)

**Hardware:** Works with virtually any printer brand (Zebra, DYMO, Brother, Epson, etc.)

**Integration: PrintNode Cloud API + Python Library**
- **How it works:** Install a lightweight PrintNode client on the computer connected to the printer. Your Django app sends print jobs to PrintNode's cloud API, which routes them to the correct printer.
- **Python library:** [PrintNode-Python](https://github.com/PrintNode/PrintNode-Python)
- **Supports:** PDF printing and RAW mode (ZPL/EPL for thermal printers)
- **OS support:** Windows, macOS, Linux, Raspberry Pi

**Pricing:**
| Plan | Price | Notes |
|------|-------|-------|
| Starter | $9/month | Single account, individual use |
| Integrator Standard | $60/month | Multi-account, client management |
| Integrator Large | $500/month | High volume |
| Self-hosted | Contact sales | On-premise server |

**Django Integration Example:**
```python
from printnodeapi import Gateway

gateway = Gateway(apikey=PRINTNODE_API_KEY)

def print_qr_label(printer_id, pdf_content):
    """Send a PDF label to any printer via PrintNode."""
    import base64
    gateway.PrintJob(
        printer=printer_id,
        title="QR Label",
        contentType="pdf_base64",
        content=base64.b64encode(pdf_content).decode(),
        source="qr-inventory-system"
    )
```

**Pros:**
- Works with any printer brand — can use cheaper hardware
- Python library available, easy Django integration
- Supports PDF (generate labels with Pillow/ReportLab, send as PDF)
- Can manage multiple printers across locations

**Cons:**
- Requires PrintNode client installed on a local machine
- Monthly subscription cost
- Extra network hop (Django -> PrintNode cloud -> local client -> printer)

---

### Option 3: Brother QL Series + Direct Network Print (Budget Option)

**Hardware:**
| Model | Type | Resolution | Price Range |
|-------|------|-----------|-------------|
| Brother QL-820NWB | Desktop | 300 DPI | ~$180-250 |
| Brother QL-1110NWB | Wide format | 300 DPI | ~$250-350 |

**Integration:** Direct network printing via IPP/CUPS or Brother b-PAC SDK
- Can be driven from Python using `python-brotherqlweb` or direct socket printing
- Alternatively, use PrintNode as middleware for cloud capability

**Pros:**
- Most affordable hardware option
- 300 DPI — good QR code quality
- WiFi/Bluetooth/USB connectivity
- Die-cut label support (pre-cut labels for consistent sizing)

**Cons:**
- Less robust API ecosystem than Zebra
- May need middleware (PrintNode) for reliable cloud triggering
- Smaller label sizes than industrial printers

---

### Option 4: BIXOLON + B-gate WebApp SDK (Web-First)

**Hardware:** BIXOLON thermal label printers with B-gate hub
- **B-gate** is a smart Ethernet-to-USB hub that enables web-based printing
- JavaScript SDK for direct browser-to-printer communication

**Pros:**
- JavaScript SDK designed for web applications
- Includes `makeQRCODE` API function specifically for QR codes
- No cloud service dependency — prints over local network

**Cons:**
- Requires B-gate hub hardware (~$200 additional)
- Less common in US market
- JavaScript-based (would need a different approach than Django server-side)

---

## Integration Architecture for QR Inventory System

### Recommended Approach: Django Signal + Print Service

```
[User submits shipment form]
        |
        v
[Django view creates InventoryItems]
        |
        v
[Django post_save signal fires]
        |
        v
[Print service generates ZPL/PDF labels]
        |
        v
[API call to Zebra SendFileToPrinter / PrintNode]
        |
        v
[Printer outputs QR labels automatically]
```

### Implementation Steps

1. **Add printer configuration to Django settings:**
   - `PRINTER_BACKEND` (zebra/printnode/none)
   - `PRINTER_API_KEY`
   - `PRINTER_ID` (target printer identifier)

2. **Create a `printing` module** in the inventory app:
   - `label_generator.py` — Generate ZPL or PDF labels from InventoryItem data
   - `print_service.py` — Abstract printer backend (Zebra API / PrintNode / local)
   - `signals.py` — Django signal handler to auto-print on shipment creation

3. **Hook into existing shipment flow:**
   - After `add_shipment` view creates items, trigger print job
   - Add print status tracking (queued/printed/failed) to InventoryItem model
   - Add retry logic for failed print jobs

4. **Dashboard additions:**
   - Print status indicator on inventory items
   - Manual "Reprint" button per item
   - Printer status/health check endpoint

---

## Recommendation

**For the QR Inventory System, the best fit is:**

### Primary: Zebra ZD421 + SendFileToPrinter API

- **Why:** Direct cloud API with no middleware, free tier covers typical usage, industry-standard ZPL for crisp QR labels, and the REST API integrates cleanly with the existing Django/Python stack using the `requests` library already in the project's dependencies.
- **Cost:** ~$350-500 for hardware + free API tier (100 prints/day)
- **Setup complexity:** Low — register on Zebra developer portal, connect printer to WiFi, add API key to Django settings.

### Fallback: PrintNode + Brother QL-820NWB

- **Why:** Lower hardware cost, brand-agnostic flexibility, official Python library.
- **Cost:** ~$180-250 hardware + $9/month API subscription
- **Setup complexity:** Medium — requires PrintNode client installed on a local machine.

---

## Sources

- [Zebra SendFileToPrinter API](https://developer.zebra.com/apis/sendfiletoprinter-model)
- [Zebra Cloud Printing Overview](https://developer.zebra.com/blog/use-sendfiletoprinter-api-your-cloud-based-printing-needs)
- [Print from a Web Application - Zebra](https://developer.zebra.com/content/print-web-application)
- [PrintNode Cloud Printing](https://www.printnode.com/en)
- [PrintNode Python Library](https://github.com/PrintNode/PrintNode-Python)
- [HPRT Label Printer APIs & SDKs Guide](https://www.hprt.com/blog/Label-Printer-APIs-and-SDKs-Key-to-Efficient-System-Integration.html)
- [BIXOLON B-gate WebApp Print SDK](https://docs.bixolon.com/index.php?kind=apis&key=24)
- [JustLabel REST API Printing](https://justlabel.io/docs-en/tutorials/rest-api-printing/)
- [TEKLYNX SENTINEL Automation](https://www.teklynx.com/en/products/enterprise-label-management-solutions/sentinel)
- [Best QR Code Label Printers 2026](https://www.qrcode-tiger.com/qr-code-label-printer)
