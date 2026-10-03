"""Belegungsdashboard – Start der Desktop-Anwendung.

    python belegungsdashboard_gui.py [Pfad zur Pivot-Datei]

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

from PySide6.QtCore import Qt, QTimer  # noqa: E402
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


def main() -> int:
    logging_einrichten()
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("Belegungsdashboard")
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
    fenster.show()

    def system_theme_folgen():
        if speicher.einstellungen().get("theme", "system") == "system":
            theme.setzen("system")
            zustand.theme_geaendert.emit()
    try:
        app.styleHints().colorSchemeChanged.connect(lambda _s: system_theme_folgen())
    except AttributeError:
        pass

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
