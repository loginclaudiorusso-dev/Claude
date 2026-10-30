@echo off
rem Neue Oberflaeche starten. Beim ersten Start wird eine eigene Python-Umgebung (modern_ui\.venv) angelegt
rem und die Pakete werden installiert (einmalig, ca. 1-3 Minuten). Das bisherige Programm bleibt unveraendert.
chcp 65001 >nul
cd /d "%~dp0"

rem Kopierte oder beschaedigte Umgebung (z. B. vom alten PC mitkopiert): pruefen und dann neu anlegen
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
    if errorlevel 1 (
        echo Die Python-Umgebung passt nicht zu diesem PC - sie wird neu angelegt ...
        rmdir /s /q ".venv"
    )
)

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv .venv
    ) else (
        rem Bewaehrte Version bevorzugen - fuer ganz neue Python-Versionen gibt es oft noch keine fertigen Pakete
        py -3.13 -m venv .venv <nul >nul 2>nul || py -3.12 -m venv .venv <nul >nul 2>nul || py -3.11 -m venv .venv <nul >nul 2>nul || py -3 -m venv .venv
    )
)
if not exist ".venv\Scripts\python.exe" (
    echo Python wurde nicht gefunden. Bitte Python 3.13 von python.org installieren - Haken bei "Add Python to PATH".
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
        echo Tipp: Bei sehr neuen Python-Versionen fehlen oft fertige Pakete. Python 3.13 installieren
        echo ^(python.org oder "py install 3.13"^), den Ordner modern_ui\.venv loeschen und neu starten.
        pause
        exit /b 1
    )
    rem Eigenes Fenster (pywebview). Klappt das nicht, oeffnet sich die Oberflaeche in einem Edge-Fenster.
    ".venv\Scripts\python.exe" -m pip install "pywebview>=5" >nul 2>nul
    copy /y requirements.txt ".venv\requirements.installiert" >nul
)

start "" ".venv\Scripts\pythonw.exe" app.py %*
