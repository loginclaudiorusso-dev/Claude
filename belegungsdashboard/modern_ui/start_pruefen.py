"""1.27: Startprüfung für „INNternat starten.bat“ – läuft mit python.exe, braucht nur die Standardbibliothek.

    start_pruefen.py vorher [--minimiert] [--browser]   Python-Version prüfen, Doppelstart verhindern
    start_pruefen.py nachher                            auf das Lebenszeichen warten, Fehler sichtbar melden

Rückgabe: 0 = weiter, 2 = läuft schon (nicht noch einmal starten), 3 = Python zu alt, 1 = Start fehlgeschlagen.
Der Ordner für Lebenszeichen und Protokoll kommt aus INNTERNAT_LOKAL (setzt die Startdatei).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from modern import netz_kern, start_kern as sk  # noqa: E402  (netz_kern ist rein, ohne NiceGUI)


def melden(text: str, fehler: bool = True) -> None:
    print(text, flush=True)
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, text, "INNternat", (0x10 if fehler else 0x40) | 0x40000)  # oben
        except Exception:      # noqa: BLE001 – Meldung steht dann nur im Fenster
            pass


def vorher(argv: list[str], ordner: Path) -> int:
    art, text = sk.python_pruefen()
    if art == "alt":
        melden(text)
        return 3
    if art == "neu":
        print("Hinweis: " + text, flush=True)
    d = sk.lesen(ordner)
    if sk.lebt(d):
        if "--minimiert" in argv:                       # „Mit Windows starten“: still – es läuft ja schon
            return 2
        if d.get("port"):                               # Browser-Fenster: einfach noch einmal öffnen
            url = f"http://127.0.0.1:{d['port']}/"
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/c", "start", "", "msedge", f"--app={url}"], creationflags=0x08000000)
            else:
                import webbrowser

                webbrowser.open(url)
            return 2
        melden("INNternat ist auf diesem PC schon geöffnet – bitte unten in der Taskleiste anklicken.\n\n"
               "(Ein zweites Fenster würde dieselben Daten doppelt bearbeiten.)", fehler=False)
        return 2
    return 0


def nachher(ordner: Path) -> int:
    print("INNternat startet ...", flush=True)
    erg, d = sk.warten(ordner, time.time() - 5)
    if erg == "bereit":
        return 0
    kandidaten = [q for q in (ordner / "modern_ui.log", Path(__file__).resolve().parent / "modern_ui.log") if q.exists()]
    log = max(kandidaten, key=lambda q: q.stat().st_mtime) if kandidaten else ordner / "modern_ui.log"
    ende = sk.protokoll_ende(log)
    if erg == "fehler":
        text = f"INNternat konnte nicht starten:\n\n{d.get('fehler') or 'unbekannter Fehler'}"
    else:
        text = "INNternat hat sich nach 90 Sekunden noch nicht gemeldet."
    melden(f"{text}\n\nProtokoll: {log}\n\nLetzte Zeilen:\n{ende}\n\nTipp: „Fehlersuche.bat“ zeigt alle Meldungen.")
    return 1


def main(argv: list[str]) -> int:
    ordner = netz_kern.lokal_ordner()
    if argv[:1] == ["vorher"]:
        return vorher(argv[1:], ordner)
    if argv[:1] == ["nachher"]:
        return nachher(ordner)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
