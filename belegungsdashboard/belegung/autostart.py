"""Mit Windows starten: legt eine kleine .cmd im Autostart-Ordner des Benutzers an.

Das Dashboard startet dann unsichtbar im Infobereich (``--hintergrund``) und meldet fällige
Erinnerungen, ohne dass man es selbst öffnen muss.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .konfig import programmordner

DATEINAME = "Belegungsdashboard.cmd"
SCHALTER = "--hintergrund"


def moeglich() -> bool:
    return sys.platform == "win32" and startordner() is not None


def startordner() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def aktiv() -> bool:
    ordner = startordner()
    return bool(ordner and (ordner / DATEINAME).exists())


def befehl() -> str:
    """Inhalt der .cmd: die exe bzw. pythonw aus der .venv (sonst Start.bat)."""
    if getattr(sys, "frozen", False):
        return f'@echo off\r\nchcp 65001 >nul\r\nstart "" "{Path(sys.executable).resolve()}" {SCHALTER}\r\n'
    ordner = programmordner()
    pythonw = ordner / ".venv" / "Scripts" / "pythonw.exe"
    if pythonw.exists():
        return (f'@echo off\r\nchcp 65001 >nul\r\ncd /d "{ordner}"\r\n'
                f'start "" "{pythonw}" belegungsdashboard_gui.py {SCHALTER}\r\n')
    return f'@echo off\r\nchcp 65001 >nul\r\ncd /d "{ordner}"\r\ncall Start.bat {SCHALTER}\r\n'


def setzen(an: bool) -> None:
    ordner = startordner()
    if ordner is None:
        raise OSError("Autostart-Ordner nicht gefunden (nur unter Windows verfügbar).")
    datei = ordner / DATEINAME
    if an:
        ordner.mkdir(parents=True, exist_ok=True)
        datei.write_text(befehl(), encoding="utf-8", newline="")
    else:
        datei.unlink(missing_ok=True)
