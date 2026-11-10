"""Neue Oberfläche starten: ``python app.py`` (eigenes Fenster) bzw. ``python app.py --browser``.

Die Daten bleiben die des Hauptprogramms im Ordner darüber – dieselben Dateien, dieselben Regeln.
Im eigenen Fenster läuft es über pywebview (Edge WebView2, bei Windows 10/11 dabei). Fehlt pywebview,
öffnet sich ein Edge-Fenster im App-Modus (ohne Adressleiste) bzw. der Standardbrowser.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent))          # Hauptprogramm (belegung) – wird nur benutzt, nicht verändert

from modern import netz_kern  # noqa: E402 – rein, ohne NiceGUI

# 0.54: Alles, was nur diesen PC betrifft, liegt lokal (%LOCALAPPDATA%\INNternat) – im Netzwerkordner würden sich
# 8 PCs Protokoll, Zwischenspeicher und NiceGUI-Ablage teilen. Ohne Netzwerkstart bleibt das Protokoll, wo es war.
LOKAL = netz_kern.lokal_ordner()
try:
    LOKAL.mkdir(parents=True, exist_ok=True)
except OSError:
    LOKAL = HIER
PROTOKOLL = (LOKAL if netz_kern.netzbetrieb() else HIER) / "modern_ui.log"
if netz_kern.netzbetrieb():                       # .pyc nicht in den Netzwerkordner (setzt auch die Startdatei)
    sys.pycache_prefix = sys.pycache_prefix or str(LOKAL / "pycache")
os.environ.setdefault("NICEGUI_STORAGE_PATH", str(LOKAL / "nicegui"))

logging.basicConfig(filename=PROTOKOLL, level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
if sys.stdout is None or sys.stderr is None:      # pythonw.exe (ohne Konsole): Ausgaben ins Protokoll statt ins Leere
    _log = open(PROTOKOLL, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stdout = sys.stdout or _log
    sys.stderr = sys.stderr or _log
KONSOLE = "--konsole" in sys.argv               # 0.85: Fehlersuche.bat – Meldungen zusätzlich im schwarzen Fenster
if KONSOLE:
    logging.getLogger().addHandler(logging.StreamHandler(sys.__stderr__))


def _abbruch(t, e, tb) -> None:
    logging.getLogger("start").critical("Abbruch", exc_info=(t, e, tb))
    if KONSOLE:
        import traceback

        traceback.print_exception(t, e, tb, file=sys.__stderr__)


sys.excepthook = _abbruch

from nicegui import app, ui  # noqa: E402

from modern import oberflaeche  # noqa: E402,F401 – registriert die Seite


def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _fenster_oeffnen(url: str, minimiert: bool = False) -> None:
    if sys.platform == "win32":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", *(["/min"] if minimiert else []), "msedge", f"--app={url}"],
                             creationflags=0x08000000)
            return
        except OSError:
            pass
    webbrowser.open(url)


def _beenden_wenn_zu() -> None:
    """Im Browser-Modus: Fenster zu → nach kurzer Zeit auch den Server beenden (kein Rest im Hintergrund)."""
    async def pruefen(_client) -> None:
        await asyncio.sleep(8)
        if not any(True for _ in app.clients("/")):
            app.shutdown()

    app.on_disconnect(pruefen)


def main() -> None:
    # 0.85: INNTERNAT_BROWSER (Installationspaket mit eigenem Python): gleich das Edge-Fenster – das eigene Fenster
    # (pywebview/.NET) darf von Netzlaufwerken oft nicht starten.
    nativ = "--browser" not in sys.argv and not os.environ.get("INNTERNAT_BROWSER")
    if nativ:
        try:
            import webview  # noqa: F401
        except ImportError:
            nativ = False
    # reconnect_timeout: Rechnet das Programm einmal länger (großer Datenstand), bleibt die Seite stehen, statt nach 3 s
    # leer neu aufgebaut zu werden („nur noch Hintergrund“).
    einstellungen = dict(title="Belegung", dark=True, reload=False, language="de",
                         show_welcome_message=False, host="127.0.0.1", reconnect_timeout=30)
    minimiert = "--minimiert" in sys.argv          # „Mit Windows starten“: als Symbol in der Taskleiste, meldet Fälliges
    if nativ:
        if minimiert:
            app.native.window_args["minimized"] = True
        ui.run(native=True, window_size=(1440, 900), **einstellungen)
    else:
        port = _freier_port()
        app.on_startup(lambda: _fenster_oeffnen(f"http://127.0.0.1:{port}/", minimiert))
        _beenden_wenn_zu()
        ui.run(port=port, show=False, **einstellungen)


if __name__ in {"__main__", "__mp_main__"}:
    main()
