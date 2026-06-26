@echo off
echo =========================================
echo Arret force de PFX Extractor - Drive Bridge (Port 7862)
echo =========================================

FOR /F "tokens=5" %%T IN ('netstat -a -n -o ^| findstr :7862') DO (
    echo Fermeture du processus PID: %%T
    taskkill /F /PID %%T
)

echo PFX Extractor arrete avec succes.
pause
