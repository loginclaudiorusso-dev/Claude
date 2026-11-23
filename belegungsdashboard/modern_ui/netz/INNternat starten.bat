@echo off
rem INNternat aus dem gemeinsamen (Netzwerk-)Ordner starten.
rem   Programm\  = das Programm (wird bei einem Update ersetzt)
rem   Daten\     = die gemeinsamen Daten aller PCs (bleibt bei Updates unangetastet)
rem Die Python-Umgebung, das Protokoll und die persoenlichen Einstellungen liegen auf jedem PC lokal unter
rem %LOCALAPPDATA%\INNternat - beim ersten Start wird sie einmalig angelegt (ca. 1-3 Minuten).
chcp 65001 >nul
setlocal
rem 1.40: fremde Python-Einstellungen dieses PCs (z. B. von GIS- oder Statistik-Programmen) duerfen nicht stoeren -
rem sonst "Could not find platform independent libraries" und "No module named nicegui".
set "PYTHONHOME="
set "PYTHONPATH="
set "PYTHONSTARTUP="
set "INN=%~dp0"
set "PROG=%INN%Programm"
set "BELEGUNG_DATEN=%INN%Daten"
set "INNTERNAT_START=%~f0"
rem Eigene Instanz (z. B. Test-Installation auf einem anderen Laufwerk): INSTANZ.txt neben dieser Datei mit einem
rem Namen wie "Test" - dann eigene lokale Umgebung, eigene Einstellungen und eigene Desktop-Verknuepfung.
set "INST="
if exist "%INN%INSTANZ.txt" set /p INST=<"%INN%INSTANZ.txt"
set "INNTERNAT_INSTANZ=%INST%"
set "INNTERNAT_LOKAL=%LOCALAPPDATA%\INNternat"
set "VERKNUEPFUNG=INNternat"
if defined INST set "INNTERNAT_LOKAL=%LOCALAPPDATA%\INNternat-%INST%"
if defined INST set "VERKNUEPFUNG=INNternat %INST%"
set "PYTHONPYCACHEPREFIX=%INNTERNAT_LOKAL%\pycache"
set "VENV=%INNTERNAT_LOKAL%\venv"

if not exist "%PROG%\modern_ui\app.py" (
    echo Der Ordner "Programm" fehlt neben dieser Datei. Bitte das Paket vollstaendig entpacken.
    pause
    exit /b 1
)
if not exist "%BELEGUNG_DATEN%" mkdir "%BELEGUNG_DATEN%"
if not exist "%INNTERNAT_LOKAL%" mkdir "%INNTERNAT_LOKAL%"

rem Portables Python im Installationspaket (Ordner "Python" mit allen Paketen): keine Python-Installation noetig.
rem 1.39: einmal je PC (und nach einem neuen Python-Paket) nach %INNTERNAT_LOKAL%\Python kopieren und von dort
rem starten - aus dem Netzwerkordner waere jeder Start langsam. Klappt das Kopieren nicht: direkt aus dem Netz.
rem Auch doppelt entpackt (Python\Python\...) wird erkannt.
set "PYNETZ="
if exist "%INN%Python\pythonw.exe" set "PYNETZ=%INN%Python"
if not defined PYNETZ if exist "%INN%Python\Python\pythonw.exe" set "PYNETZ=%INN%Python\Python"
if defined PYNETZ (
    set "PYTHONNOUSERSITE=1"
    set "INNTERNAT_BROWSER=1"
    set "PYW=%PYNETZ%\pythonw.exe"
    call :python_lokal
    if errorlevel 1 exit /b 1
    goto verknuepfung
)

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
if not errorlevel 1 goto pakete_ok
rem Installationspaket: Ordner "Pakete" mit allen Windows-Paketen - Installation ohne Internet
set "OFFLINE=0"
if exist "%INN%Pakete\" (
    echo Pakete werden aus dem Ordner Pakete installiert - ohne Internet ...
    "%VENV%\Scripts\python.exe" -m pip install --no-index --find-links "%INN%Pakete" -r "%PROG%\modern_ui\requirements.txt" "pywebview>=5"
    if not errorlevel 1 set "OFFLINE=1"
)
if "%OFFLINE%"=="1" goto pakete_fertig
(
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
)
:pakete_fertig
copy /y "%PROG%\modern_ui\requirements.txt" "%VENV%\requirements.installiert" >nul
:pakete_ok

set "PYW=%VENV%\Scripts\pythonw.exe"

:verknuepfung
rem Einmalig: Verknuepfung "INNternat" auf dem Desktop dieses PCs
if not exist "%INNTERNAT_LOKAL%\verknuepfung.erstellt" (
    powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\'+$env:VERKNUEPFUNG+'.lnk'); $s.TargetPath=$env:INNTERNAT_START; $s.WorkingDirectory=$env:INNTERNAT_LOKAL; $s.WindowStyle=7; $s.Save()" >nul 2>nul
    echo ok> "%INNTERNAT_LOKAL%\verknuepfung.erstellt"
)

rem Arbeitsordner lokal (cmd kann nicht in Netzwerkpfaden \\server\... arbeiten)
rem Fehlersuche (Fehlersuche.bat): im selben Fenster mit Konsole starten, Meldungen bleiben sichtbar
if /i "%~1"=="--konsole" (
    echo Fehlersuche: INNternat laeuft in diesem Fenster - Fehlermeldungen erscheinen hier.
    echo Protokoll: %INNTERNAT_LOKAL%\modern_ui.log
    cd /d "%INNTERNAT_LOKAL%"
    "%PYW:pythonw.exe=python.exe%" "%PROG%\modern_ui\app.py" --konsole --browser
    echo.
    echo INNternat wurde beendet. Bitte dieses Fenster abfotografieren oder den Text kopieren.
    pause
    exit /b
)
rem 1.27: Python-Version pruefen und Doppelstart verhindern (schon offen: Fenster zeigen statt zweites starten)
set "PY=%PYW:pythonw.exe=python.exe%"
"%PY%" "%PROG%\modern_ui\start_pruefen.py" vorher %*
if errorlevel 3 exit /b 1
if errorlevel 2 exit /b 0
start "" /D "%INNTERNAT_LOKAL%" "%PYW%" "%PROG%\modern_ui\app.py" %*
rem 1.27: Auf das Lebenszeichen warten - scheitert der Start, erscheint die Fehlermeldung mit dem Protokoll
"%PY%" "%PROG%\modern_ui\start_pruefen.py" nachher
exit /b

:python_lokal
rem 1.40: Die lokale Kopie wird vor dem Start geprueft (import nicegui). Passt sie nicht, wird sie einmal neu
rem kopiert; klappt auch das nicht, startet INNternat mit dem Python aus dem Netzwerkordner.
set "PYSTAND=neu"
if exist "%PYNETZ%\stand.txt" set /p PYSTAND=<"%PYNETZ%\stand.txt"
set "PYLOKAL="
if exist "%INNTERNAT_LOKAL%\Python\stand.txt" set /p PYLOKAL=<"%INNTERNAT_LOKAL%\Python\stand.txt"
if not "%PYSTAND%"=="%PYLOKAL%" goto python_kopieren
call :python_testen "%INNTERNAT_LOKAL%\Python"
if not errorlevel 1 exit /b 0
echo Die Python-Kopie auf diesem PC ist unvollstaendig - sie wird neu kopiert ...
:python_kopieren
echo Python wird einmalig auf diesen PC kopiert (ca. 1-2 Minuten) ...
if exist "%INNTERNAT_LOKAL%\Python\stand.txt" del /q "%INNTERNAT_LOKAL%\Python\stand.txt" >nul 2>nul
robocopy "%PYNETZ%" "%INNTERNAT_LOKAL%\Python" /MIR /NFL /NDL /NJH /NJS /NP /R:2 /W:2 >nul
if errorlevel 8 goto python_netz
call :python_testen "%INNTERNAT_LOKAL%\Python"
if not errorlevel 1 exit /b 0
:python_netz
echo Python vom PC passt nicht - INNternat startet mit dem Python aus dem Netzwerkordner.
call :python_testen "%PYNETZ%"
if not errorlevel 1 exit /b 0
echo.
echo Das Python im Ordner "%PYNETZ%" ist unvollstaendig ^(nicegui fehlt^).
echo Bitte INNternat_Python.zip noch einmal in den INNternat-Ordner entpacken ^(Ordner Python ersetzen^).
"%PYNETZ%\python.exe" -c "import sys; print('Python:', sys.executable); print('prefix:', sys.prefix); print('Pfade:', sys.path)"
pause
exit /b 1

:python_testen
rem Setzt PYW und PYTHONHOME auf das Python im Ordner %~1 und prueft, ob alle Pakete da sind (errorlevel 0 = ok).
if not exist "%~1\pythonw.exe" exit /b 1
set "PYTHONHOME=%~1"
set "PYW=%~1\pythonw.exe"
"%~1\python.exe" -c "import nicegui, encodings" >nul 2>nul
if errorlevel 1 (
    set "PYTHONHOME="
    exit /b 1
)
exit /b 0
