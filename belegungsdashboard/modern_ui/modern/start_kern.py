"""1.27: Start absichern – Lebenszeichen, Doppelstart, Python-Version. Rein (nur Standardbibliothek), damit die
Startprüfung (``start_pruefen.py``) in Sekundenbruchteilen läuft, ohne NiceGUI oder pandas zu laden.

Das laufende Programm schreibt in ``%LOCALAPPDATA%\\INNternat\\laeuft.json`` alle ``TAKT`` Sekunden ein Lebenszeichen:
``{"pid", "port", "zustand": "startet" | "bereit" | "fehler", "zeit", "fehler", "version"}``. Ist das Lebenszeichen
älter als ``FRISCH`` Sekunden, gilt die Instanz als beendet (abgestürzt, PC aus dem Ruhezustand …) – eine liegen
gebliebene Datei blockiert also nie einen Start. Die Datei liegt lokal: Doppelstart betrifft nur DIESEN PC; mehrere
PCs dürfen gleichzeitig arbeiten (dafür gibt es die Schreibsperre im Datenordner).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

DATEI = "laeuft.json"
TAKT = 10.0                  # Sekunden zwischen zwei Lebenszeichen
FRISCH = 35.0                # älter → Instanz gilt als beendet
MIN_PYTHON = (3, 11)
GETESTET_BIS = (3, 13)


def pfad(ordner: Path) -> Path:
    return Path(ordner) / DATEI


def lesen(ordner: Path) -> dict | None:
    try:
        d = json.loads(pfad(ordner).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def schreiben(ordner: Path, zustand: str, **mehr) -> None:
    """Atomar (erst Hilfsdatei, dann umbenennen) – die Startprüfung liest nie eine halbe Datei."""
    d = {"pid": os.getpid(), "zustand": zustand, "zeit": time.time(), **mehr}
    p = pfad(ordner)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.tmp")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, p)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def entfernen(ordner: Path) -> None:
    """Beim Beenden – nur die eigene Datei (eine zweite Instanz könnte sie inzwischen geschrieben haben)."""
    d = lesen(ordner)
    if d is not None and d.get("pid") == os.getpid():
        try:
            pfad(ordner).unlink(missing_ok=True)
        except OSError:
            pass


def pid_lebt(pid) -> bool:
    """Gibt es den Prozess noch? Im Zweifel ja (dann entscheidet das Alter des Lebenszeichens)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return ctypes.GetLastError() == 5          # Zugriff verweigert = es gibt ihn
            try:
                code = ctypes.c_ulong()
                return not k.GetExitCodeProcess(h, ctypes.byref(code)) or code.value == 259   # STILL_ACTIVE
            finally:
                k.CloseHandle(h)
        except Exception:      # noqa: BLE001
            return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def lebt(d: dict | None, jetzt: float | None = None, pid: int | None = None) -> bool:
    """Läuft (oder startet) gerade eine ANDERE Instanz auf diesem PC?"""
    if not d or d.get("zustand") not in ("startet", "bereit"):
        return False
    if d.get("pid") == (os.getpid() if pid is None else pid):
        return False
    try:
        alter = (time.time() if jetzt is None else jetzt) - float(d.get("zeit", 0))
    except (TypeError, ValueError):
        return False
    return -FRISCH < alter < FRISCH and pid_lebt(d.get("pid"))   # abgestürzt → sofort neu starten dürfen


def veraltet(d: dict | None, version: str) -> bool:
    """1.47: Läuft im Hintergrund noch eine ANDERE Programmversion (z. B. nach einem Update, Fenster schon zu)?"""
    v = str((d or {}).get("version") or "")
    return bool(v) and v != version


def beenden(pid, warten: float = 6.0, schlaf=time.sleep) -> bool:
    """1.47: Alte Instanz beenden (samt Unterprozessen). True, wenn sie danach weg ist."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        if sys.platform == "win32":
            import subprocess

            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=15,
                           creationflags=0x08000000)
        else:
            import signal

            os.kill(pid, signal.SIGTERM)
    except Exception:          # noqa: BLE001 – dann entscheidet unten, ob er noch lebt
        pass
    ende = time.time() + warten
    while time.time() < ende:
        if not pid_lebt(pid):
            return True
        schlaf(0.2)
    return not pid_lebt(pid)


def python_pruefen(version: tuple[int, ...] | None = None) -> tuple[str, str]:
    """('ok' | 'neu' | 'alt', Text). 'alt' = Start abbrechen, 'neu' = nur Hinweis (noch nicht erprobt)."""
    v = tuple((version or sys.version_info)[:2])
    text = f"Python {v[0]}.{v[1]}"
    if v < MIN_PYTHON:
        return "alt", (f"{text} ist zu alt – INNternat braucht mindestens Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}. "
                       f"Bitte Python {GETESTET_BIS[0]}.{GETESTET_BIS[1]} von python.org installieren und die "
                       f"Python-Umgebung löschen (wird beim nächsten Start neu angelegt).")
    if v > GETESTET_BIS:
        return "neu", (f"{text} ist neuer als die erprobte Version {GETESTET_BIS[0]}.{GETESTET_BIS[1]}. "
                       "Läuft etwas nicht, Python 3.13 installieren und die Python-Umgebung löschen.")
    return "ok", text


def fehler_text(e: BaseException) -> str:
    return f"{type(e).__name__}: {e}"[:600]


def protokoll_ende(datei: Path, zeilen: int = 12) -> str:
    """Die letzten Zeilen des Protokolls – für die Fehlermeldung beim Start."""
    try:
        with open(datei, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 8000))
            text = f.read().decode("utf-8", errors="replace")
    except OSError:
        return ""
    return "\n".join(text.splitlines()[-zeilen:])


def warten(ordner: Path, pid_start: float, dauer: float = 90.0, schlaf=time.sleep, uhr=time.time) -> tuple[str, dict]:
    """Nach dem Start: auf das erste Lebenszeichen der NEUEN Instanz warten (geschrieben nach ``pid_start``).
    Ergebnis ('bereit' | 'fehler' | 'zeitueberschreitung', Daten)."""
    ende = uhr() + dauer
    while uhr() < ende:
        d = lesen(ordner) or {}
        if float(d.get("zeit", 0) or 0) >= pid_start - 1:
            if d.get("zustand") == "bereit":
                return "bereit", d
            if d.get("zustand") == "fehler":
                return "fehler", d
        schlaf(0.5)
    return "zeitueberschreitung", lesen(ordner) or {}
