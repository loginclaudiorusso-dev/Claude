"""1.50: Programmsymbol aus dem eigenen Logo – im Fenster, in der Taskleiste und auf der Desktop-Verknüpfung.

Das Logo gehört nicht ins Repository: Es liegt als ``INNternat_Icon.png`` (quadratisch) bzw. ``INNternat_Logo.png``
im Datenordner (Netzwerk: neben „Programm“, bleibt bei Updates erhalten) – gesucht wie das Logo in der Titelleiste.
* ``finden``: Pfad des Symbols (Icon vor Logo) oder None – dann bleibt alles wie bisher.
* ``ico_aus_png``: Windows-Symboldatei (.ico) mit dem PNG darin (ohne Zusatzpakete).
* ``windows_einrichten``: .ico in den lokalen Ordner legen und der Desktop-Verknüpfung geben (nur wenn neu/geändert).
Rein bis auf das Setzen der Verknüpfung (PowerShell, nur Windows).
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ICON_DATEI = "INNternat_Icon.png"
LOGO_DATEI = "INNternat_Logo.png"
ICO_DATEI = "INNternat.ico"


def _orte() -> list[Path]:
    from belegung import konfig

    from .standort_kern import _BASIS

    orte = (_BASIS(), _BASIS() / "Vorlagen", konfig.programmordner(), Path(__file__).resolve().parent.parent,
            konfig.programmordner() / "Vorlagen")
    return list(dict.fromkeys(orte))


def finden() -> Path | None:
    for name in (ICON_DATEI, LOGO_DATEI):
        for o in _orte():
            p = o / name
            try:
                if p.is_file() and 0 < p.stat().st_size < 3_000_000:
                    return p
            except OSError:
                continue
    return None


def ico_aus_png(png: bytes) -> bytes:
    """Eine .ico-Datei mit genau diesem PNG (Windows Vista und neuer zeigen PNG-Symbole direkt)."""
    if png[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Kein PNG-Bild.")
    breite, hoehe = struct.unpack(">II", png[16:24])
    b, h = (0 if breite >= 256 else breite), (0 if hoehe >= 256 else hoehe)
    kopf = struct.pack("<HHH", 0, 1, 1)
    eintrag = struct.pack("<BBBBHHII", b, h, 0, 0, 1, 32, len(png), 6 + 16)
    return kopf + eintrag + png


def windows_einrichten(lokal: Path, verknuepfung: str = "INNternat") -> str:
    """.ico erzeugen und der Desktop-Verknüpfung zuweisen. Rückgabe: was getan wurde ("" = nichts)."""
    quelle = finden()
    if quelle is None:
        return ""
    try:
        ico = ico_aus_png(quelle.read_bytes())
    except (OSError, ValueError):
        return ""
    ziel = Path(lokal) / ICO_DATEI
    try:
        if ziel.is_file() and ziel.read_bytes() == ico:
            return ""
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_bytes(ico)
    except OSError:
        return ""
    if sys.platform != "win32":
        return f"Symbol gespeichert: {ziel}"
    import subprocess

    befehl = ("$d=[Environment]::GetFolderPath('Desktop'); $l=Join-Path $d ($env:INN_VK + '.lnk'); "
              "if (Test-Path $l) { $s=(New-Object -ComObject WScript.Shell).CreateShortcut($l); "
              "$s.IconLocation=$env:INN_ICO + ',0'; $s.Save() }")
    try:
        import os

        subprocess.run(["powershell", "-NoProfile", "-Command", befehl], capture_output=True, timeout=30,
                       creationflags=0x08000000, env={**os.environ, "INN_VK": verknuepfung, "INN_ICO": str(ziel)})
    except Exception:                              # noqa: BLE001 – Symbol ist Komfort
        return f"Symbol gespeichert: {ziel}"
    return f"Symbol gesetzt: {ziel}"
