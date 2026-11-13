@echo off
rem Austausch mit dem neuen Programm (fuer das alte Programm). Nutzt die Python-Umgebung des alten Programms.
chcp 65001 >nul
cd /d "%~dp0"
if not exist "..\..\.venv\Scripts\pythonw.exe" (
    echo Bitte zuerst das alte Programm einmal mit Start.bat starten - dabei wird Python eingerichtet.
    pause
    exit /b 1
)
start "" "..\..\.venv\Scripts\pythonw.exe" "austausch_alt.py"
