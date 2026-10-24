"""Neue Oberfläche starten: ``python app.py`` (eigenes Fenster) bzw. ``python app.py --browser``.

Die Daten bleiben die des Hauptprogramms im Ordner darüber – dieselben Dateien, dieselben Regeln.
Im eigenen Fenster läuft es über pywebview (Edge WebView2, bei Windows 10/11 dabei). Fehlt pywebview,
öffnet sich ein Edge-Fenster im App-Modus (ohne Adressleiste) bzw. der Standardbrowser.
"""

from __future__ import annotations

import asyncio
import logging
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent))          # Hauptprogramm (belegung) – wird nur benutzt, nicht verändert

logging.basicConfig(filename=HIER / "modern_ui.log", level=logging.INFO, encoding="utf-8",
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
if sys.stdout is None or sys.stderr is None:      # pythonw.exe (ohne Konsole): Ausgaben ins Protokoll statt ins Leere
    _log = open(HIER / "modern_ui.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    sys.stdout = sys.stdout or _log
    sys.stderr = sys.stderr or _log
sys.excepthook = lambda t, e, tb: logging.getLogger("start").critical("Abbruch", exc_info=(t, e, tb))

from nicegui import app, ui  # noqa: E402

from modern import oberflaeche  # noqa: E402,F401 – registriert die Seite


def _freier_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _fenster_oeffnen(url: str) -> None:
    if sys.platform == "win32":
        try:
            subprocess.Popen(["cmd", "/c", "start", "", "msedge", f"--app={url}"], creationflags=0x08000000)
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
    nativ = "--browser" not in sys.argv
    if nativ:
        try:
            import webview  # noqa: F401
        except ImportError:
            nativ = False
    einstellungen = dict(title="Belegung", dark=True, reload=False, language="de",
                         show_welcome_message=False, host="127.0.0.1")
    if nativ:
        ui.run(native=True, window_size=(1440, 900), **einstellungen)
    else:
        port = _freier_port()
        app.on_startup(lambda: _fenster_oeffnen(f"http://127.0.0.1:{port}/"))
        _beenden_wenn_zu()
        ui.run(port=port, show=False, **einstellungen)


if __name__ in {"__main__", "__mp_main__"}:
    main()
