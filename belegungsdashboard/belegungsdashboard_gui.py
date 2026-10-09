"""Belegungsdashboard – Start der Desktop-Anwendung.

    python belegungsdashboard_gui.py [Pfad zur Pivot-Datei] [--hintergrund]

``--hintergrund`` startet unsichtbar im Infobereich (Autostart) und meldet nur Erinnerungen.
Läuft das Dashboard schon, holt ein zweiter Start nur das vorhandene Fenster nach vorn.

Ohne Argument wird die zuletzt genutzte Datei geöffnet, sonst pivot_neu.xlsx bzw. die
neueste Excel-Datei im Programmordner.
"""

from __future__ import annotations

import io
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# In einer --windowed-exe gibt es keine Konsole; print() würde sonst abstürzen.
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from PySide6.QtCore import QLocale, Qt, QTimer  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from belegung import laden, speicher  # noqa: E402
from belegung.konfig import datenordner, programmordner  # noqa: E402
from belegung.ui import theme  # noqa: E402
from belegung.ui.basis import Zustand  # noqa: E402
from belegung.ui.hauptfenster import HauptFenster  # noqa: E402


def logging_einrichten() -> None:
    handler = []
    try:
        handler.append(RotatingFileHandler(datenordner() / "belegungsdashboard.log", maxBytes=1_000_000,
                                           backupCount=2, encoding="utf-8"))
    except OSError:
        pass
    handler.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=handler)


INSTANZ = "Belegungsdashboard-" + (os.environ.get("USERNAME") or os.environ.get("USER") or "nutzer")


def _schon_offen(hintergrund: bool) -> bool:
    """Läuft schon ein Dashboard, bekommt es den Auftrag, sich zu zeigen – dieser Start endet dann.

    Läuft dort eine andere (ältere) Version, beendet sie sich und dieser Start übernimmt –
    so wirkt ein Update sofort, auch wenn das alte Dashboard noch im Infobereich lief."""
    import time

    from PySide6.QtNetwork import QLocalSocket

    from belegung import __version__

    s = QLocalSocket()
    s.connectToServer(INSTANZ)
    if not s.waitForConnected(400):
        return False
    s.write(f"{'still' if hintergrund else 'zeigen'} {__version__}".encode())
    s.waitForBytesWritten(400)
    antwort = bytes(s.readAll()) if s.waitForReadyRead(1500) else b""
    s.disconnectFromServer()
    if b"weg" not in antwort:
        return True
    for _ in range(30):                      # warten, bis die alte Version beendet ist
        time.sleep(0.1)
        probe = QLocalSocket()
        probe.connectToServer(INSTANZ)
        if not probe.waitForConnected(100):
            return False
        probe.disconnectFromServer()
    return False


def _instanz_server(fenster: HauptFenster):
    from PySide6.QtNetwork import QLocalServer

    server = QLocalServer()
    QLocalServer.removeServer(INSTANZ)       # Reste nach einem Absturz
    if not server.listen(INSTANZ):
        return None

    def neu():
        verbindung = server.nextPendingConnection()
        if verbindung is None:
            return

        def lesen():
            from belegung import __version__

            text = bytes(verbindung.readAll()).decode("utf-8", "replace").split()
            fremd = len(text) > 1 and text[1] != __version__
            if fremd:                        # andere Version startet → Platz machen
                verbindung.write(b"weg")
                verbindung.flush()
                verbindung.waitForBytesWritten(500)
                QTimer.singleShot(200, fenster.beenden)
            elif text and text[0] == "zeigen":
                fenster.vorholen()
        verbindung.readyRead.connect(lesen)
        if verbindung.bytesAvailable():
            lesen()
    server.newConnection.connect(neu)
    return server


def _kanal_umstellen() -> None:
    """Einmalig: Outlook-Erinnerungen als Vorgabe auf den Dashboard-Kalender umstellen."""
    e = speicher.einstellungen()
    if e.get("kanal_app_umgestellt"):
        return
    erin = dict(e.get("erinnerung", {}))
    if erin.get("kanal") in ("outlook", "mail"):
        erin["kanal"] = "app"
        speicher.einstellung_setzen("erinnerung", erin)
    speicher.einstellung_setzen("kanal_app_umgestellt", True)


def main() -> int:
    logging_einrichten()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Belegungsdashboard")
    from belegung.ui.widgets import MausradSperre

    app._mausrad = MausradSperre(app)            # Mausrad verstellt keine Auswahllisten/Zahlenfelder
    app.installEventFilter(app._mausrad)
    QLocale.setDefault(QLocale(QLocale.German, QLocale.Germany))   # Kalender mit deutschen Monats-/Tagesnamen
    hintergrund = "--hintergrund" in sys.argv[1:]
    if not os.environ.get("BELEGUNG_SELFTEST") and _schon_offen(hintergrund):
        return 0
    _kanal_umstellen()
    app.setFont(theme.schrift())
    icon_pfad = programmordner() / "assets" / "icon.ico"
    if icon_pfad.exists():
        app.setWindowIcon(QIcon(str(icon_pfad)))

    modus = os.environ.get("BELEGUNG_THEME") or speicher.einstellungen().get("theme", "system")
    theme.setzen(modus)

    zustand = Zustand()
    argumente = [a for a in sys.argv[1:] if not a.startswith("-")]
    zustand.quelle = Path(argumente[0]) if argumente else laden.excel_suchen()
    if zustand.quelle is not None:
        speicher.einstellung_setzen("quelle", str(zustand.quelle))

    fenster = HauptFenster(zustand)
    fenster._instanz = _instanz_server(fenster)
    if not (hintergrund and fenster.tray is not None):   # sonst unsichtbar im Infobereich
        fenster.show()

    def system_theme_folgen():
        if speicher.einstellungen().get("theme", "system") == "system":
            theme.setzen("system")
            zustand.theme_geaendert.emit()
    try:
        app.styleHints().colorSchemeChanged.connect(lambda _s: system_theme_folgen())
    except AttributeError:
        pass

    if not hintergrund or (zustand.quelle is not None and zustand.quelle.exists()):
        QTimer.singleShot(0, lambda: fenster.laden(False))
    _selbsttest(app, fenster, zustand)
    return app.exec()


def _selbsttest(app: QApplication, fenster: HauptFenster, zustand: Zustand) -> None:
    """BELEGUNG_SELFTEST=<ordner>: nach dem Laden Screenshots aller Seiten speichern und beenden."""
    ziel = os.environ.get("BELEGUNG_SELFTEST")
    if not ziel:
        return
    ordner = Path(ziel)
    ordner.mkdir(parents=True, exist_ok=True)
    seiten = (os.environ.get("BELEGUNG_SEITEN") or ",".join(fenster.seiten)).split(",")
    fragen = [f for f in (os.environ.get("BELEGUNG_FRAGEN") or "").split("|") if f]

    def los():
        schritte = []
        for key in seiten:
            schritte.append(lambda k=key: fenster.zeigen(k))
            if key == "assistent" and fragen:
                for f in fragen:
                    schritte.append(lambda f=f: fenster.seiten["assistent"].senden(f))
            schritte.append(lambda k=key: fenster.grab().save(str(ordner / f"{k}.png")))
        schritte.append(app.quit)
        for i, s in enumerate(schritte):
            QTimer.singleShot(700 * (i + 1), s)

    zustand.daten_geaendert.connect(los)


if __name__ == "__main__":
    sys.exit(main())
