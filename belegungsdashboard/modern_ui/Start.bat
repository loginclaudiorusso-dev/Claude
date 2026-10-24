@echo off
rem Neue Oberflaeche starten. Beim ersten Start wird eine eigene Python-Umgebung (modern_ui\.venv) angelegt
rem und die Pakete werden installiert (einmalig, ca. 1-3 Minuten). Das bisherige Programm bleibt unveraendert.
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
)
if not exist ".venv\Scripts\python.exe" (
    echo Python wurde nicht gefunden. Bitte Python 3.11 oder neuer von python.org installieren.
    pause
    exit /b 1
)

fc /b requirements.txt ".venv\requirements.installiert" >nul 2>nul
if errorlevel 1 (
    echo Pakete werden installiert bzw. aktualisiert ...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Installation fehlgeschlagen - siehe Meldungen oben.
        pause
        exit /b 1
    )
    rem Eigenes Fenster (pywebview). Klappt das nicht, oeffnet sich die Oberflaeche in einem Edge-Fenster.
    ".venv\Scripts\python.exe" -m pip install "pywebview>=5" >nul 2>nul
    copy /y requirements.txt ".venv\requirements.installiert" >nul
)

start "" ".venv\Scripts\pythonw.exe" app.py
