@echo off
:: ============================================
::  Brother QL-820NWB Print Worker
:: ============================================
::
::  EDIT THESE TWO VALUES before running:
::

set PRINT_API_SECRET=CHANGE_ME
set SITE_URL=https://web-production-57c20.up.railway.app

:: ============================================
::  Printer settings (usually no changes needed)
:: ============================================

set PRINTER_MODEL=QL-820NWB
set PRINTER_URI=usb://0x04f9:0x209d
set LABEL_SIZE=62
set POLL_INTERVAL=5
set PRINTER_BACKEND=pyusb

:: ============================================

if "%PRINT_API_SECRET%"=="CHANGE_ME" (
    echo ERROR: Edit this file and set your PRINT_API_SECRET first!
    echo Open start_printer.bat in Notepad and change CHANGE_ME to your secret.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo Starting print worker...
echo Press Ctrl+C to stop.
echo.
python print_worker.py
pause
