@echo off
TITLE PriVaultHub Air-Gapped Enclave Orchestrator
color 0A

echo =======================================================================
echo          PriVaultHub Air-Gapped Local System Orchestrator
echo =======================================================================
echo.

:: -------------------------------------------------------------------------
:: 0. Check if Python is Installed
:: -------------------------------------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Error: Python is not installed or not added to your system PATH.
    echo Please install Python 3.x and ensure "Add Python to PATH" is checked.
    pause
    exit /b
)

:: -------------------------------------------------------------------------
:: 1. Activate Python Virtual Environment
:: -------------------------------------------------------------------------
echo [+] Checking Python Virtual Environment...
if exist "venv\Scripts\activate.bat" goto ACTIVATE_VENV
if exist ".venv\Scripts\activate.bat" goto ACTIVATE_DOT_VENV

echo [!] Creating 'venv' virtual environment...
python -m venv venv
if exist "venv\Scripts\activate.bat" goto ACTIVATE_VENV
goto ENV_ERROR

:ACTIVATE_VENV
call "venv\Scripts\activate.bat"
goto ENV_READY

:ACTIVATE_DOT_VENV
call ".venv\Scripts\activate.bat"
goto ENV_READY

:ENV_ERROR
echo [X] Error: Could not set up virtual environment.
pause
exit /b

:ENV_READY
echo [✓] Virtual environment active.

:: -------------------------------------------------------------------------
:: 2. Verify Dependencies & Tesseract Binary
:: -------------------------------------------------------------------------
echo.
echo [+] Verifying core dependencies (FastAPI, Uvicorn, Pytesseract, Pillow)...
python -m pip install --upgrade pip
pip install fastapi uvicorn pytesseract pillow pymupdf python-multipart httpx --quiet
echo [✓] Python dependencies verified.

echo.
echo [+] Checking Tesseract-OCR Engine binary...
if not exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [!] WARNING: Tesseract-OCR engine not found at default Windows path!
    echo [!] OCR scan features will fail until Tesseract is installed.
    echo [!] Download from: https://github.com/UB-Mannheim/tesseract/wiki
) else (
    echo [✓] Tesseract engine detected.
)

:: -------------------------------------------------------------------------
:: 3. Launch Frontend Static Server (Port 8080) in a separate window
:: -------------------------------------------------------------------------
echo.
echo [+] Launching PWA Frontend Server on http://localhost:8080 ...
start cmd /k "title PriVaultHub Frontend (Port 8080) & python -m http.server 8080"

:: -------------------------------------------------------------------------
:: 4. Launch FastAPI Backend Tesseract OCR Server (Port 8000)
:: -------------------------------------------------------------------------
echo.
echo =======================================================================
echo  Launching Tesseract OCR Backend Server on http://0.0.0.0:8000
echo =======================================================================
echo.

if exist "server.py" (
    uvicorn server:app --reload --host 0.0.0.0 --port 8000
) else if exist "main.py" (
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
) else (
    echo [X] Error: Neither server.py nor main.py found!
    pause
    exit /b
)

pause