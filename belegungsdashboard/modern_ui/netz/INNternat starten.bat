@echo off
rem INNternat aus dem gemeinsamen (Netzwerk-)Ordner starten.
rem   Programm\  = das Programm (wird bei einem Update ersetzt)
rem   Daten\     = die gemeinsamen Daten aller PCs (bleibt bei Updates unangetastet)
rem Die Python-Umgebung, das Protokoll und die persoenlichen Einstellungen liegen auf jedem PC lokal unter
rem %LOCALAPPDATA%\INNternat - beim ersten Start wird sie einmalig angelegt (ca. 1-3 Minuten).
chcp 65001 >nul
setlocal
set "INN=%~dp0"
set "PROG=%INN%Programm"
set "BELEGUNG_DATEN=%INN%Daten"
set "INNTERNAT_START=%~f0"
set "INNTERNAT_LOKAL=%LOCALAPPDATA%\INNternat"
set "PYTHONPYCACHEPREFIX=%INNTERNAT_LOKAL%\pycache"
set "VENV=%INNTERNAT_LOKAL%\venv"

if not exist "%PROG%\modern_ui\app.py" (
    echo Der Ordner "Programm" fehlt neben dieser Datei. Bitte das Paket vollstaendig entpacken.
    pause
    exit /b 1
)
if not exist "%BELEGUNG_DATEN%" mkdir "%BELEGUNG_DATEN%"
if not exist "%INNTERNAT_LOKAL%" mkdir "%INNTERNAT_LOKAL%"

rem Kaputte oder kopierte Umgebung erkennen und neu anlegen
if exist "%VENV%\Scripts\python.exe" (
    "%VENV%\Scripts\python.exe" -c "import sys" >nul 2>nul
    if errorlevel 1 (
        echo Die Python-Umgebung passt nicht zu diesem PC - sie wird neu angelegt ...
        rmdir /s /q "%VENV%"
    )
)
if not exist "%VENV%\Scripts\python.exe" (
    echo Erster Start auf diesem PC: Python-Umgebung wird angelegt ...
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv "%VENV%"
    ) else (
        py -3.13 -m venv "%VENV%" <nul >nul 2>nul || py -3.12 -m venv "%VENV%" <nul >nul 2>nul || py -3.11 -m venv "%VENV%" <nul >nul 2>nul || py -3 -m venv "%VENV%"
    )
)
if not exist "%VENV%\Scripts\python.exe" (
    echo Python wurde nicht gefunden. Bitte Python 3.13 von python.org installieren - Haken bei "Add Python to PATH".
    pause
    exit /b 1
)

fc /b "%PROG%\modern_ui\requirements.txt" "%VENV%\requirements.installiert" >nul 2>nul
if errorlevel 1 (
    echo Pakete werden installiert bzw. aktualisiert ...
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip >nul
    "%VENV%\Scripts\python.exe" -m pip install -r "%PROG%\modern_ui\requirements.txt"
    if errorlevel 1 (
        echo Installation fehlgeschlagen - siehe Meldungen oben.
        echo Tipp: Python 3.13 installieren, den Ordner %VENV% loeschen und neu starten.
        pause
        exit /b 1
    )
    "%VENV%\Scripts\python.exe" -m pip install "pywebview>=5" >nul 2>nul
    copy /y "%PROG%\modern_ui\requirements.txt" "%VENV%\requirements.installiert" >nul
)

rem Einmalig: Verknuepfung "INNternat" auf dem Desktop dieses PCs
if not exist "%INNTERNAT_LOKAL%\verknuepfung.erstellt" (
    powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\INNternat.lnk'); $s.TargetPath=$env:INNTERNAT_START; $s.WorkingDirectory=$env:INNTERNAT_LOKAL; $s.WindowStyle=7; $s.Save()" >nul 2>nul
    echo ok> "%INNTERNAT_LOKAL%\verknuepfung.erstellt"
)

rem Arbeitsordner lokal (cmd kann nicht in Netzwerkpfaden \\server\... arbeiten)
start "" /D "%INNTERNAT_LOKAL%" "%VENV%\Scripts\pythonw.exe" "%PROG%\modern_ui\app.py" %*
