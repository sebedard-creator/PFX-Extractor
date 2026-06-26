@echo off
cd /d "%~dp0"
echo =========================================
echo Lancement de PFX Extractor - Drive Bridge...
echo =========================================

REM Verifier si l'environnement virtuel existe
if not exist ".venv" (
    echo Initialisation de l'environnement virtuel...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installation des dependances...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo Lancement de l'application LAN...
python app_local.py
pause
