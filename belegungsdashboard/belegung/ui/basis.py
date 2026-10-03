"""Gemeinsamer App-Zustand, Hintergrund-Worker und Basisklasse für Seiten."""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

from ..datenstand import Datenstand
from ..konfig import GESAMT

log = logging.getLogger(__name__)


class Zustand(QObject):
    """Globale Auswahl + aktueller Datenstand. Seiten reagieren auf die Signale."""

    daten_geaendert = Signal()
    filter_geaendert = Signal()
    theme_geaendert = Signal()
    navigieren = Signal(str)
    meldung = Signal(str, str)          # Text, Art (ok|warnung|fehler|info)
    neu_laden = Signal(bool)            # refresh vom Server?
    listen_geaendert = Signal()         # Import/Kapazität/manuell -> neu berechnen

    def __init__(self):
        super().__init__()
        self.ds: Datenstand | None = None
        self.quelle: Path | None = None
        self.standort: str = GESAMT
        self.brutto: bool = False
        self.laedt: bool = False

    def standort_setzen(self, standort: str) -> None:
        if standort != self.standort:
            self.standort = standort
            self.filter_geaendert.emit()

    def brutto_setzen(self, brutto: bool) -> None:
        if brutto != self.brutto:
            self.brutto = brutto
            self.filter_geaendert.emit()


class Worker(QThread):
    """Führt eine Funktion im Hintergrund aus. Bei COM-Zugriff (Excel) mit CoInitialize."""

    fortschritt = Signal(str)
    fertig = Signal(object)
    fehler = Signal(str)

    def __init__(self, funktion: Callable, *args, com: bool = False, parent=None, **kwargs):
        super().__init__(parent)
        self._f, self._args, self._kwargs, self._com = funktion, args, kwargs, com

    def run(self):
        pythoncom = None
        if self._com:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pythoncom = None
        try:
            self.fertig.emit(self._f(*self._args, **self._kwargs))
        except Exception as exc:
            log.error("Hintergrundaufgabe fehlgeschlagen:\n%s", traceback.format_exc())
            self.fehler.emit(str(exc) or type(exc).__name__)
        finally:
            if pythoncom is not None:
                pythoncom.CoUninitialize()


class Seite(QWidget):
    """Scrollbare Seite. ``aktualisieren`` läuft nur, wenn die Seite sichtbar ist; sonst
    wird sie als veraltet markiert und beim nächsten Anzeigen neu gezeichnet."""

    titel = ""
    untertitel = ""
    zeigt_filter = True
    zeigt_bezug = True
    scrollbar = True

    def __init__(self, zustand: Zustand, parent=None):
        super().__init__(parent)
        self.z = zustand
        self._veraltet = True
        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(0, 0, 0, 0)
        inhalt = QWidget()
        inhalt.setObjectName("seiteninhalt")
        if self.scrollbar:
            self.scroll = QScrollArea()
            self.scroll.setWidgetResizable(True)
            self.scroll.setFrameShape(QFrame.NoFrame)
            self.scroll.setWidget(inhalt)
            aussen.addWidget(self.scroll)
        else:
            aussen.addWidget(inhalt)
        self.lay = QVBoxLayout(inhalt)
        self.lay.setContentsMargins(28, 8, 28, 28)
        self.lay.setSpacing(16)
        zustand.daten_geaendert.connect(self.anstossen)
        zustand.filter_geaendert.connect(self.anstossen)
        zustand.theme_geaendert.connect(self._theme)

    def zeile(self, *widgets: QWidget, stretch: list[int] | None = None) -> QHBoxLayout:
        """Karten nebeneinander, alle so hoch wie die höchste."""
        behaelter = QWidget()
        behaelter.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        h = QHBoxLayout(behaelter)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(16)
        for i, w in enumerate(widgets):
            w.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            h.addWidget(w, (stretch or [1] * len(widgets))[i])
        self.lay.addWidget(behaelter)
        return h

    def anstossen(self) -> None:
        self._veraltet = True
        if self.isVisible() and self.z.ds is not None:
            self._ausfuehren()

    def showEvent(self, e):
        super().showEvent(e)
        if self._veraltet and self.z.ds is not None:
            self._ausfuehren()

    def _theme(self) -> None:
        self.theme_aktualisieren()
        self.anstossen()

    def _ausfuehren(self) -> None:
        self._veraltet = False
        try:
            self.aktualisieren()
        except Exception:
            log.exception("Seite %s konnte nicht aktualisiert werden", type(self).__name__)
            self.z.meldung.emit(f"Anzeige „{self.titel}“ konnte nicht aktualisiert werden.", "fehler")

    def aktualisieren(self) -> None:  # pragma: no cover - in Unterklassen
        pass

    def theme_aktualisieren(self) -> None:
        """Für Elemente, die Theme-Farben selbst setzen (Icons, Punkte)."""
