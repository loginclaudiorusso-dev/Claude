"""Wiederverwendbare Bausteine. Farben kommen ausschließlich aus ``theme.T`` bzw. dem Stylesheet."""

from __future__ import annotations

import calendar
import math
from datetime import date, timedelta

from PySide6.QtCore import (
    QDate, QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, Signal,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCalendarWidget, QDateEdit, QFrame, QGraphicsOpacityEffect, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLayout, QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
    QToolButton, QVBoxLayout, QWidget,
)

from . import icons, theme

DEUTSCHE_MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September",
                   "Oktober", "November", "Dezember"]
MONATE_KURZ = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def zahl(x: float | None, nachkomma: int = 0) -> str:
    if x is None:
        return "–"
    s = f"{x:,.{nachkomma}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def prozent(anteil: float | None, nachkomma: int = 0) -> str:
    return "–" if anteil is None else f"{zahl(anteil * 100, nachkomma)} %"


def rolle(widget: QWidget, **eigenschaften) -> QWidget:
    for k, v in eigenschaften.items():
        widget.setProperty(k, v)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    return widget


def label(text: str = "", r: str | None = None, umbruch: bool = False) -> QLabel:
    lbl = QLabel(text)
    if r:
        lbl.setProperty("rolle", r)
    lbl.setWordWrap(umbruch)
    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse) if umbruch else None
    return lbl


def knopf(text: str = "", variant: str | None = None, icon_name: str | None = None, tooltip: str | None = None) -> QPushButton:
    b = QPushButton(text)
    if variant:
        b.setProperty("variant", variant)
    b.setCursor(Qt.PointingHandCursor)
    if icon_name:
        b.setProperty("icon_name", icon_name)
        icon_setzen(b)
    if tooltip:
        b.setToolTip(tooltip)
    return b


def icon_setzen(b: QPushButton | QToolButton) -> None:
    """Icon passend zum aktuellen Theme (nach Theme-Wechsel erneut aufrufen)."""
    name = b.property("icon_name")
    if not name:
        return
    t = theme.T
    variant = b.property("variant")
    farbe = t.accent_text if variant == "primary" else (t.ueber if variant == "gefahr" else t.text_2)
    b.setIcon(icons.icon(name, farbe, 16))
    b.setIconSize(QSize(16, 16))


def trenner() -> QFrame:
    f = QFrame()
    f.setProperty("trenner", True)
    return f


def leeren(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()
        elif item.layout():
            leeren(item.layout())


# ---------------------------------------------------------------------------------------
# Karten
# ---------------------------------------------------------------------------------------

class Karte(QFrame):
    def __init__(self, titel: str | None = None, untertitel: str | None = None, abstand: int = 18, parent=None):
        super().__init__(parent)
        self.setProperty("karte", True)
        # Maximum: Karten wachsen nicht über ihren Inhalt hinaus (sonst verteilt Qt bei
        # umbrechenden Labels Leerraum in die Karte). Zeilen gleichen die Höhe selbst an.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self._aussen = QVBoxLayout(self)
        self._aussen.setContentsMargins(abstand, abstand - 2, abstand, abstand)
        self._aussen.setSpacing(12)
        self.kopf = QHBoxLayout()
        self.kopf.setSpacing(8)
        self.titel_label = self.untertitel_label = None
        if titel is not None:
            texte = QVBoxLayout()
            texte.setSpacing(2)
            self.titel_label = label(titel, "kartentitel")
            texte.addWidget(self.titel_label)
            if untertitel:
                self.untertitel_label = label(untertitel, "kartenuntertitel", umbruch=True)
                texte.addWidget(self.untertitel_label)
            self.kopf.addLayout(texte, 1)
            self._aussen.addLayout(self.kopf)
        self.inhalt = QVBoxLayout()
        self.inhalt.setSpacing(10)
        self._aussen.addLayout(self.inhalt)
        self._aussen.addStretch(1)  # Resthöhe (in Zeilen mit höheren Nachbarn) nach unten

    def aktion(self, widget: QWidget) -> QWidget:
        self.kopf.addWidget(widget, 0, Qt.AlignTop)
        return widget

    def untertitel(self, text: str) -> None:
        if self.untertitel_label:
            self.untertitel_label.setText(text)


class Pille(QLabel):
    def __init__(self, text: str = "", stufe: str = "neutral"):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.setzen(stufe, text)

    def setzen(self, stufe: str, text: str) -> None:
        punkt = "●" if stufe in ("ok", "knapp", "kritisch", "ueber") else ""
        self.setText(f"{punkt} {text}".strip())
        rolle(self, pille=stufe)


class Hinweis(QFrame):
    """Hinweiszeile mit Icon (Info, Warnung, Fehler) und optionaler Aktion."""

    def __init__(self, text: str, art: str = "info", aktion: str | None = None, parent=None):
        super().__init__(parent)
        self.setProperty("hinweis", art)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 12, 9)
        lay.setSpacing(10)
        t = theme.T
        farbe = {"info": t.accent, "warnung": t.knapp, "fehler": t.ueber}[art]
        ic = QLabel()
        ic.setPixmap(icons.pixmap("info" if art == "info" else "warnung", farbe, 16))
        ic.setFixedWidth(18)
        lay.addWidget(ic, 0, Qt.AlignTop)
        self.text = label(text, umbruch=True)
        lay.addWidget(self.text, 1)
        self.knopf = None
        if aktion:
            self.knopf = knopf(aktion, "ghost")
            lay.addWidget(self.knopf, 0, Qt.AlignVCenter)


# ---------------------------------------------------------------------------------------
# Segmentierte Auswahl
# ---------------------------------------------------------------------------------------

class Segment(QFrame):
    geaendert = Signal(int)

    def __init__(self, optionen: list[str], index: int = 0, parent=None):
        super().__init__(parent)
        self.setProperty("segment", True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self._gruppe = QButtonGroup(self)
        self._gruppe.setExclusive(True)
        for i, text in enumerate(optionen):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self._gruppe.addButton(b, i)
            lay.addWidget(b)
        if optionen:
            self._gruppe.button(index).setChecked(True)
        self._gruppe.idClicked.connect(self.geaendert.emit)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)

    def index(self) -> int:
        return self._gruppe.checkedId()

    def setzen(self, index: int, still: bool = True) -> None:
        b = self._gruppe.button(index)
        if b is None:
            self._gruppe.setExclusive(False)
            for x in self._gruppe.buttons():
                x.setChecked(False)
            self._gruppe.setExclusive(True)
            return
        b.setChecked(True)
        if not still:
            self.geaendert.emit(index)


# ---------------------------------------------------------------------------------------
# Grafik-Widgets (QPainter, gestochen scharf, ohne matplotlib)
# ---------------------------------------------------------------------------------------

class Sparkline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._werte: list[float] = []
        self._ist_bis: int | None = None
        self._farbe = "#888"
        self.setMinimumHeight(38)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def setzen(self, werte: list[float], farbe: str, ist_bis: int | None = None) -> None:
        self._werte, self._farbe, self._ist_bis = list(werte), farbe, ist_bis
        self.update()

    def paintEvent(self, _):
        if len(self._werte) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 4, -4, -4)
        lo, hi = min(self._werte), max(self._werte)
        spanne = (hi - lo) or 1.0
        n = len(self._werte)
        punkte = [QPointF(r.left() + r.width() * i / (n - 1), r.bottom() - (v - lo) / spanne * r.height())
                  for i, v in enumerate(self._werte)]
        pfad = QPainterPath(punkte[0])
        for pt in punkte[1:]:
            pfad.lineTo(pt)
        flaeche = QPainterPath(pfad)
        flaeche.lineTo(punkte[-1].x(), r.bottom() + 4)
        flaeche.lineTo(punkte[0].x(), r.bottom() + 4)
        verlauf = QLinearGradient(0, r.top(), 0, r.bottom())
        c = QColor(self._farbe)
        c.setAlphaF(0.20)
        verlauf.setColorAt(0, c)
        c.setAlphaF(0.0)
        verlauf.setColorAt(1, c)
        p.fillPath(flaeche, verlauf)
        stift = QPen(QColor(self._farbe), 1.8)
        stift.setCapStyle(Qt.RoundCap)
        stift.setJoinStyle(Qt.RoundJoin)
        p.setPen(stift)
        p.drawPath(pfad)
        ende = punkte[self._ist_bis if self._ist_bis is not None else -1]
        p.setBrush(QColor(theme.T.surface))
        p.setPen(QPen(QColor(self._farbe), 2))
        p.drawEllipse(ende, 3.5, 3.5)
        p.end()


class Donut(QWidget):
    """Ringdiagramm mit Mitteltext; Segmente mit 2px Lücke, Hover zeigt Wert."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._teile: list[tuple[str, float, str]] = []
        self._mitte = ("", "")
        self._hover: int | None = None
        self.setMouseTracking(True)
        self.setMinimumSize(180, 180)

    def setzen(self, teile: list[tuple[str, float, str]], mitte: str, unten: str) -> None:
        self._teile = [(n, max(w, 0.0), f) for n, w, f in teile if w > 0]
        self._mitte = (mitte, unten)
        self.update()

    def _geometrie(self) -> tuple[QRectF, float]:
        seite = min(self.width(), self.height()) - 8
        r = QRectF((self.width() - seite) / 2, (self.height() - seite) / 2, seite, seite)
        return r, seite * 0.13

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = theme.T
        r, dicke = self._geometrie()
        ring = r.adjusted(dicke / 2, dicke / 2, -dicke / 2, -dicke / 2)
        summe = sum(w for _, w, _ in self._teile)
        if summe <= 0:
            p.setPen(QPen(QColor(t.surface_2), dicke, Qt.SolidLine, Qt.FlatCap))
            p.drawArc(ring, 0, 360 * 16)
        else:
            start = 90.0
            luecke = 1.2 if len(self._teile) > 1 else 0
            for i, (_, w, farbe) in enumerate(self._teile):
                winkel = 360.0 * w / summe
                breite = dicke * (1.12 if i == self._hover else 1.0)
                p.setPen(QPen(QColor(farbe), breite, Qt.SolidLine, Qt.FlatCap))
                p.drawArc(ring, int((start - luecke / 2) * 16), int(-(winkel - luecke) * 16))
                start -= winkel
        p.setPen(QColor(t.text))
        f = self.font()
        f.setPixelSize(int(r.height() * 0.16))
        f.setWeight(f.Weight.Bold)
        p.setFont(f)
        oben = QRectF(r.left(), r.center().y() - r.height() * 0.15, r.width(), r.height() * 0.2)
        p.drawText(oben, Qt.AlignCenter, self._mitte[0])
        f.setPixelSize(max(11, int(r.height() * 0.065)))
        f.setWeight(f.Weight.Normal)
        p.setFont(f)
        p.setPen(QColor(t.text_2))
        unten = QRectF(r.left(), r.center().y() + r.height() * 0.05, r.width(), r.height() * 0.1)
        p.drawText(unten, Qt.AlignCenter, self._mitte[1])
        p.end()

    def mouseMoveEvent(self, e):
        r, dicke = self._geometrie()
        c = r.center()
        dx, dy = e.position().x() - c.x(), e.position().y() - c.y()
        abstand = math.hypot(dx, dy)
        idx = None
        if r.width() / 2 - dicke * 1.2 <= abstand <= r.width() / 2 + 2 and self._teile:
            winkel = (90 - math.degrees(math.atan2(-dy, dx))) % 360
            summe = sum(w for _, w, _ in self._teile)
            akk = 0.0
            for i, (_, w, _) in enumerate(self._teile):
                akk += 360 * w / summe
                if winkel <= akk:
                    idx = i
                    break
        if idx != self._hover:
            self._hover = idx
            self.update()
        if idx is not None:
            n, w, _ = self._teile[idx]
            summe = sum(x for _, x, _ in self._teile)
            self.setToolTip(f"{n}: {zahl(w)} ({zahl(100 * w / summe)} %)")
        else:
            self.setToolTip("")

    def leaveEvent(self, _):
        self._hover = None
        self.update()


class Legende(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lay = QGridLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setHorizontalSpacing(10)
        self._lay.setVerticalSpacing(6)

    def setzen(self, eintraege: list[tuple[str, str, str]]) -> None:
        """(Farbe, Name, Wert-Text)"""
        leeren(self._lay)
        for i, (farbe, name, wert) in enumerate(eintraege):
            punkt = QLabel()
            punkt.setFixedSize(10, 10)
            punkt.setStyleSheet(f"background: {farbe}; border-radius: 3px;")
            self._lay.addWidget(punkt, i, 0, Qt.AlignVCenter)
            self._lay.addWidget(label(name, "muted"), i, 1)
            w = label(wert, "fett")
            w.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._lay.addWidget(w, i, 2)
        self._lay.setColumnStretch(1, 1)


class Balken(QWidget):
    """Horizontaler Fortschrittsbalken für Auslastung mit Schwellenmarken."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._anteil: float | None = None
        self._farbe = "#888"
        self.setFixedHeight(8)

    def setzen(self, anteil: float | None, farbe: str) -> None:
        self._anteil, self._farbe = anteil, farbe
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = theme.T
        r = QRectF(self.rect())
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t.surface_2))
        p.drawRoundedRect(r, 4, 4)
        if self._anteil is not None:
            b = QRectF(r.left(), r.top(), r.width() * min(self._anteil, 1.0), r.height())
            p.setBrush(QColor(self._farbe))
            p.drawRoundedRect(b, 4, 4)
        p.end()


# ---------------------------------------------------------------------------------------
# KPI-Karte
# ---------------------------------------------------------------------------------------

class KpiKarte(Karte):
    geklickt = Signal()

    def __init__(self, titel: str, farbe_punkt: str | None = None, sparkline: bool = True, parent=None):
        super().__init__(parent=parent, abstand=16)
        self.inhalt.setSpacing(6)
        kopf = QHBoxLayout()
        kopf.setSpacing(7)
        self.punkt = QLabel()
        self.punkt.setFixedSize(8, 8)
        self.punkt.setVisible(farbe_punkt is not None)
        kopf.addWidget(self.punkt, 0, Qt.AlignVCenter)
        self.titel = label(titel, "kpi_label")
        kopf.addWidget(self.titel, 1)
        self.pille = Pille()
        self.pille.setVisible(False)
        kopf.addWidget(self.pille)
        self.inhalt.addLayout(kopf)
        wert_zeile = QHBoxLayout()
        wert_zeile.setSpacing(6)
        self.wert = label("–", "kpi_wert")
        wert_zeile.addWidget(self.wert, 0, Qt.AlignBottom)
        self.einheit = label("", "klein")
        wert_zeile.addWidget(self.einheit, 0, Qt.AlignBottom)
        wert_zeile.addStretch()
        self.delta = label("", "klein")
        wert_zeile.addWidget(self.delta, 0, Qt.AlignBottom)
        self.inhalt.addLayout(wert_zeile)
        self.balken = Balken()
        self.balken.setVisible(False)
        self.inhalt.addWidget(self.balken)
        self.detail = label("", "kpi_detail")
        self.inhalt.addWidget(self.detail)
        self.spark = Sparkline() if sparkline else None
        if self.spark:
            self.inhalt.addWidget(self.spark)
        self.farbe_punkt(farbe_punkt)

    def farbe_punkt(self, farbe: str | None) -> None:
        if farbe:
            self.punkt.setStyleSheet(f"background: {farbe}; border-radius: 4px;")

    def mousePressEvent(self, e):
        if self.property("klickbar"):
            self.geklickt.emit()
        super().mousePressEvent(e)


# ---------------------------------------------------------------------------------------
# Datum & Zeitraum
# ---------------------------------------------------------------------------------------

def qdate(d: date) -> QDate:
    return QDate(d.year, d.month, d.day)


def pydate(q: QDate) -> date:
    return date(q.year(), q.month(), q.day())


class DatumFeld(QWidget):
    geaendert = Signal(object)

    def __init__(self, d: date, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.feld = QDateEdit(qdate(d))
        self.feld.setDisplayFormat("dd.MM.yyyy")
        self.feld.setButtonSymbols(QDateEdit.NoButtons)
        self.feld.setFixedWidth(118)
        self.feld.dateChanged.connect(lambda q: self.geaendert.emit(pydate(q)))
        lay.addWidget(self.feld)
        self.btn = QToolButton(self)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.setToolTip("Kalender öffnen")
        self.btn.clicked.connect(self._oeffnen)
        self.btn.setFixedSize(26, 26)
        self.icon_aktualisieren()
        lay.addWidget(self.btn)
        self._kal = QCalendarWidget()
        self._kal.setWindowFlags(Qt.Popup)
        self._kal.setGridVisible(False)
        self._kal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self._kal.setFirstDayOfWeek(Qt.Monday)
        self._kal.clicked.connect(self._gewaehlt)

    def icon_aktualisieren(self) -> None:
        self.btn.setIcon(icons.icon("kalender", theme.T.text_2, 16))

    def _oeffnen(self):
        self._kal.setSelectedDate(self.feld.date())
        pos = self.mapToGlobal(QPoint(0, self.height() + 4))
        self._kal.move(pos)
        self._kal.show()

    def _gewaehlt(self, q: QDate):
        self._kal.hide()
        self.feld.setDate(q)

    def datum(self) -> date:
        return pydate(self.feld.date())

    def setzen(self, d: date, still: bool = True) -> None:
        self.feld.blockSignals(still)
        self.feld.setDate(qdate(d))
        self.feld.blockSignals(False)


class MonatsPopup(QFrame):
    gewaehlt = Signal(int, int)

    def __init__(self, jahr: int, monat: int, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setProperty("karte", True)
        self._jahr, self._auswahl = jahr, (jahr, monat)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        kopf = QHBoxLayout()
        zurueck = knopf("", "icon", "links")
        vor = knopf("", "icon", "rechts")
        self._jahr_label = label(str(jahr), "fett")
        self._jahr_label.setAlignment(Qt.AlignCenter)
        zurueck.clicked.connect(lambda: self._jahr_wechseln(-1))
        vor.clicked.connect(lambda: self._jahr_wechseln(1))
        kopf.addWidget(zurueck)
        kopf.addWidget(self._jahr_label, 1)
        kopf.addWidget(vor)
        lay.addLayout(kopf)
        self._gitter = QGridLayout()
        self._gitter.setSpacing(4)
        lay.addLayout(self._gitter)
        self._bauen()

    def _jahr_wechseln(self, d: int):
        self._jahr += d
        self._jahr_label.setText(str(self._jahr))
        self._bauen()

    def _bauen(self):
        leeren(self._gitter)
        for i, name in enumerate(MONATE_KURZ):
            b = knopf(name, "primary" if (self._jahr, i + 1) == self._auswahl else "ghost")
            b.setFixedSize(54, 30)
            b.clicked.connect(lambda _=False, m=i + 1: (self.gewaehlt.emit(self._jahr, m), self.close()))
            self._gitter.addWidget(b, i // 4, i % 4)


class ZeitraumLeiste(QWidget):
    """Schnellwahl (30 T, 90 T, 6 M, 12 M, 24 M, Jahr) + Von/Bis + Monatssprung."""

    geaendert = Signal(object, object)
    VORGABEN = [("30 T", 30), ("90 T", 90), ("6 M", 182), ("12 M", 365), ("24 M", 730), ("lfd. Jahr", -1)]

    def __init__(self, ende: date, vorgabe: int = 1, parent=None):
        super().__init__(parent)
        self._ende = ende
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        self.segment = Segment([n for n, _ in self.VORGABEN], vorgabe)
        self.segment.geaendert.connect(self._vorgabe)
        lay.addWidget(self.segment)
        lay.addSpacing(6)
        self.von = DatumFeld(ende)
        self.bis = DatumFeld(ende)
        self.von.geaendert.connect(self._manuell)
        self.bis.geaendert.connect(self._manuell)
        lay.addWidget(self.von)
        lay.addWidget(label("–", "muted"))
        lay.addWidget(self.bis)
        self.monat = knopf("Monat", "ghost", "kalender", "Direkt zu einem Monat springen")
        self.monat.clicked.connect(self._monat_popup)
        lay.addWidget(self.monat)
        lay.addStretch()
        self._vorgabe(vorgabe, melden=False)

    def ende_setzen(self, ende: date) -> None:
        self._ende = ende
        if self.segment.index() >= 0:
            self._vorgabe(self.segment.index())

    def zeitraum(self) -> tuple[date, date]:
        return self.von.datum(), self.bis.datum()

    def _vorgabe(self, idx: int, melden: bool = True):
        _, tage = self.VORGABEN[idx]
        bis = self._ende
        von = date(bis.year, 1, 1) if tage < 0 else bis - timedelta(days=tage - 1)
        self._setzen(von, bis, melden)

    def _setzen(self, von: date, bis: date, melden: bool = True):
        self.von.setzen(von)
        self.bis.setzen(bis)
        if melden:
            self.geaendert.emit(von, bis)

    def _manuell(self, _):
        von, bis = self.zeitraum()
        if von > bis:
            return
        self.segment.setzen(-1)
        self.geaendert.emit(von, bis)

    def _monat_popup(self):
        von = self.von.datum()
        popup = MonatsPopup(von.year, von.month, self)
        popup.gewaehlt.connect(self._monat_gewaehlt)
        popup.move(self.monat.mapToGlobal(QPoint(0, self.monat.height() + 4)))
        popup.show()

    def _monat_gewaehlt(self, jahr: int, monat: int):
        self.segment.setzen(-1)
        self._setzen(date(jahr, monat, 1), date(jahr, monat, calendar.monthrange(jahr, monat)[1]))


# ---------------------------------------------------------------------------------------
# Tabelle
# ---------------------------------------------------------------------------------------

class Tabelle(QTableWidget):
    def __init__(self, kopf: list[str], ausrichtung: list[str] | None = None, dehnen: int = 0, parent=None):
        super().__init__(0, len(kopf), parent)
        self.setHorizontalHeaderLabels(kopf)
        self._ausrichtung = ausrichtung or ["l"] + ["r"] * (len(kopf) - 1)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAlternatingRowColors(False)
        self.setWordWrap(False)
        kh = self.horizontalHeader()
        kh.setHighlightSections(False)
        kh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        kh.setStretchLastSection(False)
        kh.setSectionResizeMode(QHeaderView.ResizeToContents)
        kh.setSectionResizeMode(dehnen, QHeaderView.Stretch)
        self.verticalHeader().setDefaultSectionSize(36)

    def fuellen(self, zeilen: list[list], farben: dict[tuple[int, int], str] | None = None) -> None:
        self.setRowCount(len(zeilen))
        for r, zeile in enumerate(zeilen):
            for c, wert in enumerate(zeile):
                if isinstance(wert, QWidget):
                    self.setCellWidget(r, c, wert)
                    continue
                item = QTableWidgetItem("" if wert is None else str(wert))
                links = self._ausrichtung[c] == "l" if c < len(self._ausrichtung) else True
                item.setTextAlignment((Qt.AlignLeft if links else Qt.AlignRight) | Qt.AlignVCenter)
                if farben and (r, c) in farben:
                    item.setForeground(QColor(farben[(r, c)]))
                self.setItem(r, c, item)

    def hoehe_anpassen(self, max_zeilen: int = 14) -> None:
        n = min(self.rowCount(), max_zeilen)
        self.setFixedHeight(self.horizontalHeader().height() + n * self.verticalHeader().defaultSectionSize() + 4)


# ---------------------------------------------------------------------------------------
# Layout-Helfer
# ---------------------------------------------------------------------------------------

class FlowLayout(QLayout):
    """Umbrechende Zeile (für Vorschlags-Chips)."""

    def __init__(self, parent=None, abstand: int = 8):
        super().__init__(parent)
        self._items: list = []
        self._abstand = abstand
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, breite):
        return self._anordnen(QRect(0, 0, breite, 0), testen=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._anordnen(rect)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for item in self._items:
            s = s.expandedTo(item.minimumSize())
        return s

    def _anordnen(self, rect: QRect, testen: bool = False) -> int:
        x, y, zeile = rect.x(), rect.y(), 0
        for item in self._items:
            w = item.sizeHint()
            if x + w.width() > rect.right() and zeile > 0:
                x, y, zeile = rect.x(), y + zeile + self._abstand, 0
            if not testen:
                item.setGeometry(QRect(QPoint(x, y), w))
            x += w.width() + self._abstand
            zeile = max(zeile, w.height())
        return y + zeile - rect.y()


class Toast(QFrame):
    """Kurze Rückmeldung unten rechts, blendet sich selbst aus."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toast")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 16, 10)
        lay.setSpacing(10)
        self._icon = QLabel()
        lay.addWidget(self._icon)
        self._text = QLabel()
        self._text.setWordWrap(True)
        self._text.setMaximumWidth(380)
        lay.addWidget(self._text)
        self._effekt = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effekt)
        self._anim = QPropertyAnimation(self._effekt, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._timer = QTimer(self, singleShot=True, timeout=self._ausblenden)
        self.hide()

    def zeigen(self, text: str, art: str = "ok", dauer_ms: int = 3200) -> None:
        t = theme.T
        name, farbe = {"ok": ("haken", t.ok), "warnung": ("warnung", t.knapp), "fehler": ("warnung", t.ueber),
                       "info": ("info", t.tooltip_text)}[art]
        self._icon.setPixmap(icons.pixmap(name, farbe, 16))
        self._text.setText(text)
        self.adjustSize()
        p = self.parentWidget()
        self.move(p.width() - self.width() - 24, p.height() - self.height() - 24)
        self.raise_()
        self.show()
        self._anim.stop()
        self._anim.setDuration(180)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(dauer_ms)

    def _ausblenden(self):
        self._anim.stop()
        self._anim.setDuration(300)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._fertig)
        self._anim.start()

    def _fertig(self):
        self._anim.finished.disconnect(self._fertig)
        self.hide()


class Leer(QWidget):
    """Leerzustand mit Icon, Titel, Text und optionaler Aktion."""

    def __init__(self, icon_name: str, titel: str, text: str, aktion: str | None = None, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 26, 20, 26)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)
        ic = QLabel()
        ic.setPixmap(icons.pixmap(icon_name, theme.T.text_3, 30))
        ic.setAlignment(Qt.AlignCenter)
        lay.addWidget(ic)
        t = label(titel, "fett")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)
        tx = label(text, "muted", umbruch=True)
        tx.setAlignment(Qt.AlignCenter)
        tx.setMaximumWidth(420)
        lay.addWidget(tx, 0, Qt.AlignCenter)
        self.knopf = None
        if aktion:
            self.knopf = knopf(aktion, "primary")
            lay.addWidget(self.knopf, 0, Qt.AlignCenter)
