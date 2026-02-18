@echo off
echo ============================================
echo  Brother QL-820NWB Print Worker Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate and install
echo Installing dependencies...
call venv\Scripts\activate.bat
pip install -r print_worker_requirements.txt

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo Next steps:
echo   1. Edit start_printer.bat and set your PRINT_API_SECRET
echo   2. Run start_printer.bat to start the print worker
echo.
pause
