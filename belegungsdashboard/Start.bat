@echo off
rem Belegungsdashboard starten. Beim ersten Start wird eine eigene Python-Umgebung (.venv)
rem angelegt und die benötigten Pakete werden installiert (einmalig, ca. 2-5 Minuten).
rem Kommen mit einer neuen Version Pakete dazu, werden sie beim nächsten Start nachinstalliert.
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        where python >nul 2>nul
        if errorlevel 1 (
            echo Python wurde nicht gefunden. Bitte Python 3.11 oder neuer von python.org installieren
            echo und dabei "Add python.exe to PATH" anhaken. Danach Start.bat erneut ausfuehren.
            pause
            exit /b 1
        )
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
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
    copy /y requirements.txt ".venv\requirements.installiert" >nul
)

rem Nach einem Update: ein noch laufendes altes Dashboard (z. B. unsichtbar im Infobereich) beenden,
rem sonst würde dieser Start nur das alte Fenster nach vorn holen.
fc /b belegung\__init__.py ".venv\version.gestartet" >nul 2>nul
if errorlevel 1 (
    powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*belegungsdashboard_gui.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>nul
    copy /y belegung\__init__.py ".venv\version.gestartet" >nul
)

start "" ".venv\Scripts\pythonw.exe" belegungsdashboard_gui.py %*
