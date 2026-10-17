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
    termine_geaendert = Signal()        # Termin angelegt/erledigt -> Kalender und Erinnerungen neu
    name_geaendert = Signal()           # Name des Dashboards geändert (Seitenleiste, Fenstertitel)
    zimmer_geaendert = Signal()         # Zimmerplan (Zuweisung, Stammdaten, Gebäudeplan) -> andere Fenster neu
    aenderung_gespeichert = Signal(str, str)   # wie meldung, aber mit „Rückgängig“ (aenderungen.letzter())

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


def sichtbar(w: QWidget) -> bool:
    """Wirklich zu sehen: sichtbar und das Fenster nicht minimiert bzw. im Infobereich versteckt.
    Nur dann wird neu gerechnet und gezeichnet – sonst wird es beim Zurückholen nachgeholt."""
    fenster = w.window()
    return w.isVisible() and fenster is not None and not fenster.isMinimized()


def arbeitsspeicher_freigeben() -> None:
    """Beim Minimieren: Zwischenspeicher leeren und (unter Windows) ungenutzten Arbeitsspeicher abgeben."""
    import gc
    import sys

    from PySide6.QtGui import QPixmapCache

    QPixmapCache.clear()
    gc.collect()
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.psapi.EmptyWorkingSet(ctypes.windll.kernel32.GetCurrentProcess())
        except Exception:          # noqa: BLE001 – rein kosmetisch, darf nie stören
            pass


class Seite(QWidget):
    """Scrollbare Seite. ``aktualisieren`` läuft nur, wenn die Seite sichtbar ist; sonst
    wird sie als veraltet markiert und beim nächsten Anzeigen neu gezeichnet."""

    titel = ""
    untertitel = ""
    zeigt_filter = True
    zeigt_bezug = True
    scrollbar = True
    reiter_attr: str | None = None      # Name des Segments mit Unterreitern (für Tabs: Ansicht merken)

    def __init__(self, zustand: Zustand, parent=None):
        super().__init__(parent)
        self.z = zustand
        self._veraltet = True
        aussen = QVBoxLayout(self)
        aussen.setContentsMargins(0, 0, 0, 0)
        aussen.setSpacing(0)
        # Angeheftet: Reiter u. Ä. scrollen nicht mit (``anheften``) – bleibt leer und unsichtbar, wenn unbenutzt
        self._kopf_w = QWidget()
        self._kopf_w.setObjectName("seiteninhalt")
        self.kopf_fest = QVBoxLayout(self._kopf_w)
        self.kopf_fest.setContentsMargins(28, 8, 28, 8)
        self.kopf_fest.setSpacing(10)
        self._kopf_w.hide()
        aussen.addWidget(self._kopf_w)
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

    def anheften(self, element, ausrichtung=None) -> None:
        """Widget oder Layout oben anheften – es bleibt beim Scrollen stehen (z. B. die Reiter)."""
        self._kopf_w.show()
        if isinstance(element, QWidget):
            if ausrichtung is not None:
                self.kopf_fest.addWidget(element, 0, ausrichtung)
            else:
                self.kopf_fest.addWidget(element)
        else:
            self.kopf_fest.addLayout(element)

    # ---- Ansicht für Tabs: welcher Unterreiter usw. ----------------------------------------

    def _reiter_segment(self):
        return getattr(self, self.reiter_attr, None) if self.reiter_attr else None

    def ansicht_lesen(self) -> dict:
        r = self._reiter_segment()
        return {"reiter": r.index()} if r is not None else {}

    def ansicht_setzen(self, ansicht: dict) -> None:
        r, i = self._reiter_segment(), ansicht.get("reiter")
        if r is not None and isinstance(i, int) and i >= 0 and i != r.index():
            r.setzen(i, still=False)

    def ansicht_titel(self) -> str:
        """Kurzer Zusatz für den Tab, z. B. „Zeitstrahl“ (ohne Zähler wie „(27)“)."""
        import re

        r = self._reiter_segment()
        return re.sub(r"\s*\(\d+\)$", "", r.beschriftung(r.index())) if r is not None else ""

    def anstossen(self) -> None:
        self._veraltet = True
        if sichtbar(self) and self.z.ds is not None:
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
