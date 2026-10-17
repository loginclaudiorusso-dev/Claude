"""Wiederverwendbare Bausteine. Farben kommen ausschließlich aus ``theme.T`` bzw. dem Stylesheet."""

from __future__ import annotations

import calendar
import math
import re
from datetime import date, timedelta

from PySide6.QtCore import (
    QDate, QEasingCurve, QEvent, QObject, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, Qt, QTimer, Signal,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QDateEdit, QFrame, QGraphicsOpacityEffect, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLayout, QMenu, QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem,
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


class KurzLabel(QLabel):
    """Einzeiliges Label, das bei wenig Platz mit „…“ kürzt (voller Text im Tooltip) statt zu verbreitern."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._voll = ""
        self.setText(text)

    def setText(self, text: str) -> None:
        self._voll = text
        self.setToolTip(text)
        self._kuerzen()

    def text_voll(self) -> str:
        return self._voll

    def minimumSizeHint(self) -> QSize:
        return QSize(60, super().minimumSizeHint().height())

    def sizeHint(self) -> QSize:
        return QSize(self.fontMetrics().horizontalAdvance(self._voll) + 4, super().sizeHint().height())

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self._kuerzen()

    def _kuerzen(self) -> None:
        QLabel.setText(self, self.fontMetrics().elidedText(self._voll, Qt.ElideRight, max(self.width(), 60)))


class FettKnopf(QPushButton):
    """Knopf, der genug Platz für fette Schrift reserviert – gewählte Reiter/Chips werden fett und
    würden sonst abgeschnitten („Reinigung“ → „Reinigunc“)."""

    def sizeHint(self):
        s = super().sizeHint()
        if not self.text():
            return s
        from PySide6.QtGui import QFont, QFontMetrics

        fett = QFont(self.font())
        fett.setBold(True)
        mehr = QFontMetrics(fett).horizontalAdvance(self.text()) - self.fontMetrics().horizontalAdvance(self.text())
        return QSize(s.width() + max(mehr, 0) + 4, s.height())

    def minimumSizeHint(self):
        return self.sizeHint()


def knopf(text: str = "", variant: str | None = None, icon_name: str | None = None, tooltip: str | None = None) -> QPushButton:
    b = FettKnopf(text) if variant == "chip" else QPushButton(text)
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
    b.setIcon(icons.icon(name, farbe, 16, t.accent if variant == "chip" else None))   # Chip an: Akzentfarbe
    b.setIconSize(QSize(16, 16))


def trenner() -> QFrame:
    f = QFrame()
    f.setProperty("trenner", True)
    return f


def leeren(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()          # sofort weg – gelöscht wird erst später
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

    def __init__(self, optionen: list[str], index: int = 0, parent=None, trenner: tuple[int, ...] = (),
                 tipps: list[str] | None = None):
        """``trenner``: vor diesen Positionen ein senkrechter Strich (Gruppen); ``tipps``: Tooltip je Option."""
        super().__init__(parent)
        self.setProperty("segment", True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self._gruppe = QButtonGroup(self)
        self._gruppe.setExclusive(True)
        for i, text in enumerate(optionen):
            if i in trenner:
                strich = QFrame()
                strich.setFrameShape(QFrame.VLine)
                strich.setFixedWidth(9)
                strich.setStyleSheet(f"color: {theme.alpha(theme.T.text_3, .45)};")
                lay.addWidget(strich)
            b = FettKnopf(text)
            if tipps and i < len(tipps) and tipps[i]:
                b.setToolTip(tipps[i])
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self._gruppe.addButton(b, i)
            lay.addWidget(b)
        if optionen:
            self._gruppe.button(index).setChecked(True)
        self._gruppe.idClicked.connect(self.geaendert.emit)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self._eng = False
        self._normal_breite = 0

    def eng_wenn_noetig(self, verfuegbar: int) -> None:
        """Weniger Innenabstand, wenn die Reiter sonst nicht in die Breite passen (kein waagrechtes Scrollen)."""
        if not self._eng:
            self._normal_breite = self.sizeHint().width()
        soll = self._normal_breite > verfuegbar
        if soll != self._eng:
            self._eng = soll
            self.setStyleSheet("QPushButton { padding-left: 7px; padding-right: 7px; }" if soll else "")
            for b in self._gruppe.buttons():
                b.updateGeometry()

    def index(self) -> int:
        return self._gruppe.checkedId()

    def beschriftung(self, index: int) -> str:
        b = self._gruppe.button(index)
        return b.text().replace("&&", "&") if b is not None else ""

    def text_setzen(self, index: int, text: str) -> None:
        b = self._gruppe.button(index)
        if b is not None and b.text() != text:
            b.setText(text)
            b.updateGeometry()

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
        self.titel.setWordWrap(True)                 # lange Titel umbrechen statt die Zeile zu verbreitern
        kopf.addWidget(self.titel, 1)
        self.pille = Pille()
        self.pille.setVisible(False)
        kopf.addWidget(self.pille)
        self.delta = KurzLabel()                    # Trend rechts im Kopf: kürzt bei schmalen Karten statt zu verbreitern
        self.delta.setProperty("rolle", "klein")
        self.delta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.delta.setMinimumWidth(1)               # leer (z. B. Seite Belegung) oder sehr schmal: keine Mindestbreite
        kopf.addWidget(self.delta, 1, Qt.AlignVCenter)
        self.inhalt.addLayout(kopf)
        wert_zeile = QHBoxLayout()
        wert_zeile.setSpacing(6)
        self.wert = label("–", "kpi_wert")
        wert_zeile.addWidget(self.wert, 0, Qt.AlignBottom)
        self.einheit = label("", "klein")
        self.einheit.setWordWrap(True)               # lange Einheiten umbrechen statt die Karte zu verbreitern
        wert_zeile.addWidget(self.einheit, 1, Qt.AlignBottom)
        wert_zeile.addStretch()
        self.inhalt.addLayout(wert_zeile)
        self.balken = Balken()
        self.balken.setVisible(False)
        self.inhalt.addWidget(self.balken)
        self.detail = label("", "kpi_detail")
        self.detail.setWordWrap(True)
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


WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class KalenderPopup(QFrame):
    """Eigener Monatskalender (statt QCalendarWidget, dessen Zellen die Tabellen-Abstände erben und „…“ zeigen).
    Feste Zellgröße, Heute umrandet, Auswahl gefüllt, Tage der Nachbarmonate blass, Wochenende ruhig.
    Pfeile/Mausrad blättern Monate, „Heute“ springt zurück."""

    gewaehlt = Signal(object)
    ZELLE = QSize(36, 32)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("kalender")
        self._auswahl = date.today()
        self._monat = self._auswahl.replace(day=1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)
        kopf = QHBoxLayout()
        kopf.setSpacing(4)
        self._zurueck = QToolButton()
        self._vor = QToolButton()
        for b, d, tip in ((self._zurueck, -1, "Vorheriger Monat"), (self._vor, 1, "Nächster Monat")):
            b.setObjectName("kal_pfeil")
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(tip)
            b.setFixedSize(30, 30)
            b.clicked.connect(lambda _=False, d=d: self._blaettern(d))
        self._titel = QLabel()
        self._titel.setObjectName("kal_titel")
        self._titel.setAlignment(Qt.AlignCenter)
        kopf.addWidget(self._zurueck)
        kopf.addWidget(self._titel, 1)
        kopf.addWidget(self._vor)
        lay.addLayout(kopf)
        self._gitter = QGridLayout()
        self._gitter.setSpacing(2)
        for i, name in enumerate(WOCHENTAGE_KURZ):
            l = QLabel(name)
            l.setObjectName("kal_wotag")
            l.setAlignment(Qt.AlignCenter)
            self._gitter.addWidget(l, 0, i)
        self._tage: list[QPushButton] = []
        for r in range(6):
            for c in range(7):
                b = QPushButton()
                b.setObjectName("kal_tag")
                b.setFixedSize(self.ZELLE)
                b.setCursor(Qt.PointingHandCursor)
                b.setFocusPolicy(Qt.NoFocus)
                b.clicked.connect(lambda _=False, b=b: self._klick(b))
                self._gitter.addWidget(b, r + 1, c)
                self._tage.append(b)
        lay.addLayout(self._gitter)
        fuss = QHBoxLayout()
        heute = QPushButton("Heute")
        heute.setObjectName("kal_heute")
        heute.setCursor(Qt.PointingHandCursor)
        heute.clicked.connect(lambda: self._waehlen(date.today()))
        fuss.addStretch()
        fuss.addWidget(heute)
        lay.addLayout(fuss)
        self.stil()

    def stil(self) -> None:
        t = theme.T
        self.setStyleSheet(f"""
            QFrame#kalender {{ background: {t.surface}; border: 1px solid {t.border_strong}; border-radius: 10px; }}
            QLabel#kal_titel {{ color: {t.text}; font-weight: 600; font-size: 14px; }}
            QLabel#kal_wotag {{ color: {t.text_3}; font-size: 11px; font-weight: 600; padding: 2px 0; }}
            QToolButton#kal_pfeil {{ border: none; border-radius: 6px; background: transparent; }}
            QToolButton#kal_pfeil:hover {{ background: {t.hover}; }}
            QPushButton#kal_tag {{ border: 1px solid transparent; border-radius: 7px; background: transparent;
                                   color: {t.text}; padding: 0; font-size: 13px;
                                   min-width: {self.ZELLE.width()}px; max-width: {self.ZELLE.width()}px;
                                   min-height: {self.ZELLE.height()}px; max-height: {self.ZELLE.height()}px; }}
            QPushButton#kal_tag:hover {{ background: {t.hover}; }}
            QPushButton#kal_tag[art="wochenende"] {{ color: {t.text_2}; }}
            QPushButton#kal_tag[art="fremd"] {{ color: {t.text_3}; }}
            QPushButton#kal_tag[heute="true"] {{ border-color: {t.accent}; color: {t.accent}; font-weight: 700; }}
            QPushButton#kal_tag[gewaehlt="true"] {{ background: {t.accent}; color: {t.accent_text}; font-weight: 700; }}
            QPushButton#kal_heute {{ border: none; background: transparent; color: {t.accent}; font-weight: 600;
                                     padding: 4px 8px; min-height: 0; }}
            QPushButton#kal_heute:hover {{ background: {t.accent_soft}; border-radius: 6px; }}
        """)
        self._zurueck.setIcon(icons.icon("links", t.text_2, 16))
        self._vor.setIcon(icons.icon("rechts", t.text_2, 16))

    def zeigen(self, d: date, pos: QPoint) -> None:
        self._auswahl = d
        self._monat = d.replace(day=1)
        self.stil()
        self._fuellen()
        self.adjustSize()
        bildschirm = self.screen().availableGeometry() if self.screen() else None
        if bildschirm is not None:           # nicht aus dem Bildschirm ragen (z. B. Feld ganz unten)
            pos.setX(min(pos.x(), bildschirm.right() - self.width()))
            if pos.y() + self.height() > bildschirm.bottom():
                pos.setY(pos.y() - self.height() - 40)
        self.move(pos)
        self.show()

    def _fuellen(self) -> None:
        self._titel.setText(f"{DEUTSCHE_MONATE[self._monat.month - 1]} {self._monat.year}")
        start = self._monat - timedelta(days=self._monat.weekday())
        heute = date.today()
        for i, b in enumerate(self._tage):
            d = start + timedelta(days=i)
            b.tag = d
            b.setText(str(d.day))
            b.setProperty("art", "fremd" if d.month != self._monat.month else ("wochenende" if d.weekday() >= 5 else ""))
            b.setProperty("heute", d == heute)
            b.setProperty("gewaehlt", d == self._auswahl)
            b.setToolTip(f"{WOCHENTAGE_KURZ[d.weekday()]} {d:%d.%m.%Y}")
            b.style().unpolish(b)
            b.style().polish(b)

    def _blaettern(self, d: int) -> None:
        m = self._monat.month - 1 + d
        self._monat = date(self._monat.year + m // 12, m % 12 + 1, 1)
        self._fuellen()

    def _klick(self, b: QPushButton) -> None:
        self._waehlen(b.tag)

    def _waehlen(self, d: date) -> None:
        self._auswahl = d
        self.hide()
        self.gewaehlt.emit(d)

    def wheelEvent(self, e) -> None:
        self._blaettern(-1 if e.angleDelta().y() > 0 else 1)
        e.accept()

    def keyPressEvent(self, e) -> None:
        if e.key() in (Qt.Key_PageUp, Qt.Key_Left):
            self._blaettern(-1)
        elif e.key() in (Qt.Key_PageDown, Qt.Key_Right):
            self._blaettern(1)
        else:
            super().keyPressEvent(e)


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
        self._kal: KalenderPopup | None = None        # erst beim ersten Öffnen bauen (spart Start-Zeit)

    def icon_aktualisieren(self) -> None:
        self.btn.setIcon(icons.icon("kalender", theme.T.text_2, 16))

    def _oeffnen(self):
        if self._kal is None:
            self._kal = KalenderPopup(self)
            self._kal.gewaehlt.connect(self._gewaehlt)
        self._kal.zeigen(self.datum(), self.mapToGlobal(QPoint(0, self.height() + 4)))

    def _gewaehlt(self, d: date):
        self.feld.setDate(qdate(d))

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
        fluss = FlowLayout(self, abstand=10)           # Schnellwahl und Von/Bis brechen im schmalen Fenster um
        self.segment = Segment([n for n, _ in self.VORGABEN], vorgabe)
        self.segment.geaendert.connect(self._vorgabe)
        fluss.addWidget(self.segment)
        datum = QWidget()
        lay = QHBoxLayout(datum)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        fluss.addWidget(datum)
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

class MausradSperre(QObject):
    """Mausrad über Auswahllisten und Zahlenfeldern ändert nichts – die Seite scrollt einfach weiter.
    Erst in der per Klick geöffneten Liste wirkt das Rad. Als Event-Filter an der QApplication."""

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Wheel:
            from PySide6.QtWidgets import QAbstractSpinBox, QComboBox

            if isinstance(obj, (QComboBox, QAbstractSpinBox)):
                self._weiterreichen(obj, e)
                return True
        return False

    @staticmethod
    def _weiterreichen(obj, e) -> None:
        """An den nächsten Bildlaufbereich darüber (Tabelle, dann Seite), der in diese Richtung noch scrollen kann."""
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QAbstractScrollArea, QApplication

        runter = e.angleDelta().y() < 0 or e.pixelDelta().y() < 0
        w = obj.parentWidget()
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                bar = w.verticalScrollBar()
                if (bar.value() < bar.maximum()) if runter else (bar.value() > bar.minimum()):
                    vp = w.viewport()
                    pos = vp.mapFromGlobal(e.globalPosition().toPoint())
                    QApplication.sendEvent(vp, QWheelEvent(pos, e.globalPosition(), e.pixelDelta(), e.angleDelta(),
                                                           e.buttons(), e.modifiers(), e.phase(), e.inverted()))
                    return
            w = w.parentWidget()


_DATUM = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})")
_ZAHL = re.compile(r"^-?\d{1,3}(?:\.\d{3})*(?:,\d+)?$|^-?\d+(?:[.,]\d+)?$")
INDEX = Qt.UserRole + 41          # Zeile in den Daten des Aufrufers (bleibt beim Sortieren erhalten)
SORTTEXT = Qt.UserRole + 42       # Sortiertext für Zellen mit Widget (Pille, Auswahl …)


_ZIMMER = re.compile(r"^(?:GS-)?(\d+(?:\.\d+)?)-([A-Z]?)(\d+)")
_DATUM_KURZ = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2})?(?!\d)")


def sortierschluessel(text: str) -> tuple:
    """Zimmer nach Haus → Etage (UG, EG, 1. OG …) → Nummer; Zahlen als Zahl; Datum (TT.MM.JJJJ, auch TT.MM.[JJ])
    als Datum; sonst „natürlich“ (Groß/Klein egal); leer bzw. „– nicht zugeteilt –“ zuletzt."""
    t = (text or "").strip()
    if not t or t[0] in "–—" or t == "-":
        return (3,)
    m = _ZIMMER.match(t)
    if m:
        haus, buchstabe, nr = float(m.group(1)), m.group(2), int(m.group(3))
        etage = {"U": -1, "E": 0}.get(buchstabe, nr // 100 if not buchstabe else 50)
        return (2, 0, haus, etage, nr, t.casefold())
    m = _DATUM.match(t)
    if m:
        return (1, int(m.group(3)), int(m.group(2)), int(m.group(1)), t)
    m = _DATUM_KURZ.match(t)
    if m:
        jahr = 2000 + int(m.group(3)) if m.group(3) else 0
        return (1, jahr, int(m.group(2)), int(m.group(1)), t)
    z = t.rstrip(" %€").strip()
    if _ZAHL.match(z):
        try:
            return (0, float(z.replace(".", "").replace(",", ".") if "," in z else z), t)
        except ValueError:
            pass
    return (2, 1, tuple((0, int(p), "") if p.isdigit() else (1, 0, p.casefold()) for p in re.split(r"(\d+)", t) if p))


def widget_text(w: QWidget | None) -> str:
    """Sichtbarer Wert eines Zellen-Widgets – auch in einem Container (Auswahlliste mit Häkchen daneben)."""
    if w is None:
        return ""
    from PySide6.QtWidgets import QAbstractButton, QComboBox

    kandidaten = [w] + w.findChildren(QComboBox) + w.findChildren(QAbstractButton) + w.findChildren(QLabel)
    for x in kandidaten:
        if isinstance(x, QComboBox):
            return x.currentText()
        if isinstance(x, QAbstractButton) and x.isCheckable() and not x.text():
            return "1" if x.isChecked() else "0"
        if callable(getattr(x, "text", None)) and isinstance(t := x.text(), str) and t.strip():
            return t
    return ""


class _Zelle(QTableWidgetItem):
    def _sorttext(self) -> str:
        tw = self.tableWidget()
        w = tw.cellWidget(self.row(), self.column()) if tw is not None else None
        if w is not None:                     # aktueller Wert (z. B. später geänderte Auswahl)
            return widget_text(w)
        return self.data(SORTTEXT) or self.text()

    def __lt__(self, other) -> bool:
        b = other._sorttext() if isinstance(other, _Zelle) else (other.text() if isinstance(other, QTableWidgetItem) else "")
        return sortierschluessel(self._sorttext()) < sortierschluessel(b)


class Tabelle(QTableWidget):
    """Tabelle im Stil der App. Klick auf eine Spaltenüberschrift sortiert auf-/absteigend (nur Tabellen, die
    über ``fuellen`` befüllt werden). ``daten_zeile``/``ansicht_zeile`` rechnen zwischen angezeigter Zeile und
    Zeile in den Daten des Aufrufers um."""

    def __init__(self, kopf: list[str], ausrichtung: list[str] | None = None, dehnen: int = 0, parent=None):
        super().__init__(0, len(kopf), parent)
        self._sortierung: tuple[int, Qt.SortOrder] | None = None
        self._mit_index = False
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
        self.verticalHeader().setDefaultSectionSize(max(36, self.fontMetrics().height() + 18))
        kh.setSectionsClickable(True)
        kh.sectionClicked.connect(self._kopf_geklickt)
        kh.setToolTip("Klicken: aufsteigend sortieren · nochmal klicken: absteigend")

    # ---- Sortieren ---------------------------------------------------------------------

    def _kopf_geklickt(self, c: int) -> None:
        kopf = self.horizontalHeaderItem(c)
        if not self._mit_index or kopf is None or not kopf.text():
            return
        reihe = Qt.DescendingOrder if self._sortierung == (c, Qt.AscendingOrder) else Qt.AscendingOrder
        self._sortierung = (c, reihe)
        self._sortieren()

    def _sortieren(self) -> None:
        if self._sortierung is None or not self._mit_index:
            return
        c, reihe = self._sortierung
        kh = self.horizontalHeader()
        kh.setSortIndicatorShown(True)
        kh.setSortIndicator(c, reihe)
        self.sortItems(c, reihe)

    def daten_zeile(self, r: int) -> int:
        """Angezeigte Zeile → Zeile in der an ``fuellen`` übergebenen Liste."""
        for c in range(self.columnCount()):
            it = self.item(r, c)
            if it is not None and it.data(INDEX) is not None:
                return int(it.data(INDEX))
        return r

    def ansicht_zeile(self, i: int) -> int:
        """Zeile in den Daten → angezeigte Zeile."""
        for r in range(self.rowCount()):
            if self.daten_zeile(r) == i:
                return r
        return i

    def fuellen(self, zeilen: list[list], farben: dict[tuple[int, int], str] | None = None) -> None:
        self.setRowCount(len(zeilen))
        for r, zeile in enumerate(zeilen):
            for c, wert in enumerate(zeile):
                if isinstance(wert, QWidget):
                    platz = _Zelle("")               # leere Zelle unter dem Widget: Index + Sortiertext
                    platz.setData(INDEX, r)
                    platz.setData(SORTTEXT, widget_text(wert))
                    self.setItem(r, c, platz)
                    self.setCellWidget(r, c, wert)
                    continue
                if self.cellWidget(r, c) is not None:
                    self.removeCellWidget(r, c)      # sonst liegt eine alte Pille über dem neuen Text
                item = _Zelle("" if wert is None else str(wert))
                item.setData(INDEX, r)
                links = self._ausrichtung[c] == "l" if c < len(self._ausrichtung) else True
                item.setTextAlignment((Qt.AlignLeft if links else Qt.AlignRight) | Qt.AlignVCenter)
                if farben and (r, c) in farben:
                    item.setForeground(QColor(farben[(r, c)]))
                self.setItem(r, c, item)
        self._mit_index = True
        if self._sortierung is not None:      # erst nach dem Aufrufer (Tooltips je Datenzeile) neu sortieren
            QTimer.singleShot(0, self._sortieren)

    def widgets_einpassen(self, rand: int = 14) -> None:
        """Spalten und Zeilen mit eingebetteten Widgets (Auswahllisten, Häkchen, Pillen) so groß machen,
        dass nichts abgeschnitten wird – auch bei Windows-Skalierung 125/150 %."""
        kh = self.horizontalHeader()
        hoehe = max(self.verticalHeader().defaultSectionSize(), self.fontMetrics().height() + 18)
        for c in range(self.columnCount()):
            breite = 0
            for r in range(self.rowCount()):
                w = self.cellWidget(r, c)
                if w is not None:
                    w.adjustSize()
                    sh = w.sizeHint()
                    breite = max(breite, sh.width())
                    hoehe = max(hoehe, sh.height() + 6)
            if breite and kh.sectionResizeMode(c) != QHeaderView.Stretch:
                kh.setSectionResizeMode(c, QHeaderView.Fixed)
                self.setColumnWidth(c, max(breite + rand, kh.sectionSizeHint(c), self.sizeHintForColumn(c)))
        self.verticalHeader().setDefaultSectionSize(hoehe)

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
        if isinstance(parent, QWidget):
            # Höhe hängt von der Breite ab – sonst rechnen umgebende Layouts mit zu wenig Zeilen
            sp = parent.sizePolicy()
            sp.setHeightForWidth(True)
            parent.setSizePolicy(sp)

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
        # bevorzugt: alles in einer Zeile – sonst rechnen umgebende Layouts mit der Breite eines
        # einzelnen Elements und reservieren viel zu viel Höhe; schmaler geht trotzdem (minimumSize)
        if not self._items:
            return QSize()
        breite = sum(i.sizeHint().width() for i in self._items) + self._abstand * (len(self._items) - 1)
        return QSize(breite, max(i.sizeHint().height() for i in self._items))

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
        self._aktion = knopf("", "ghost")
        self._aktion.hide()
        self._aktion.clicked.connect(self._aktion_klick)
        self._rueckruf = None
        lay.addWidget(self._aktion)
        self._effekt = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effekt)
        self._anim = QPropertyAnimation(self._effekt, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._timer = QTimer(self, singleShot=True, timeout=self._ausblenden)
        self.hide()

    def zeigen(self, text: str, art: str = "ok", dauer_ms: int = 3200, aktion: tuple[str, object] | None = None) -> None:
        """``aktion`` = (Beschriftung, Funktion), z. B. („Rückgängig“, …) – dann bleibt die Meldung länger stehen."""
        t = theme.T
        self._rueckruf = aktion[1] if aktion else None
        self._aktion.setText(aktion[0] if aktion else "")
        self._aktion.setVisible(aktion is not None)
        if aktion is not None:
            dauer_ms = max(dauer_ms, 9000)
            self._aktion.setStyleSheet(f"QPushButton {{ color: {t.tooltip_text}; font-weight: 600; padding: 4px 10px; "
                                       f"border: 1px solid {theme.alpha(t.tooltip_text, .45)}; border-radius: 6px; }}"
                                       f"QPushButton:hover {{ background: {theme.alpha(t.tooltip_text, .14)}; }}")
            self._text.setMinimumWidth(min(self._text.fontMetrics().horizontalAdvance(text) + 4, 300))
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

    def _aktion_klick(self) -> None:
        rueckruf, self._rueckruf = self._rueckruf, None
        self._timer.stop()
        self.hide()
        if rueckruf is not None:
            rueckruf()

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


# ---------------------------------------------------------------------------------------
# Mehrfachauswahl (z. B. Personengruppen)
# ---------------------------------------------------------------------------------------

class _OffenesMenue(QMenu):
    """Menü, das beim Anhaken offen bleibt – so lassen sich mehrere Einträge nacheinander wählen."""

    def mouseReleaseEvent(self, e):
        a = self.activeAction()
        if a is not None and a.isCheckable() and a.isEnabled():
            a.trigger()
            return
        super().mouseReleaseEvent(e)


class Mehrfachauswahl(QPushButton):
    """Knopf mit Häkchen-Menü. ``geaendert`` liefert die Menge der gewählten Schlüssel (leer = alle)."""

    geaendert = Signal(object)

    def __init__(self, eintraege: list[tuple[str, str]], alle_text: str = "Alle", parent=None):
        super().__init__(parent)
        self._alle_text = alle_text
        self._menue = _OffenesMenue(self)
        self._aktionen: dict[str, object] = {}
        alle = self._menue.addAction("Alle zeigen")
        alle.triggered.connect(lambda: self.setzen(set()))
        self._menue.addSeparator()
        for schluessel, text in eintraege:
            a = self._menue.addAction(text)
            a.setCheckable(True)
            a.setData(text)
            a.toggled.connect(lambda _an: self._melden())
            self._aktionen[schluessel] = a
        self.setMenu(self._menue)
        self.setProperty("variant", "chip")          # mit Rahmen – als Auswahlfeld erkennbar
        self._beschriften()

    def auswahl(self) -> set[str]:
        return {k for k, a in self._aktionen.items() if a.isChecked()}

    def setzen(self, schluessel: set[str]) -> None:
        for k, a in self._aktionen.items():
            a.blockSignals(True)
            a.setChecked(k in schluessel)
            a.blockSignals(False)
        self._melden()

    def anzahl_setzen(self, zahlen: dict[str, int]) -> None:
        """Zahl hinter jedem Eintrag, z. B. „EMR (6)“."""
        for k, a in self._aktionen.items():
            a.setText(f"{a.data()} ({zahlen.get(k, 0)})" if k in zahlen else a.data())

    def _beschriften(self) -> None:
        gewaehlt = [a.data() for a in self._aktionen.values() if a.isChecked()]
        if not gewaehlt:
            self.setText(self._alle_text)
        elif len(gewaehlt) <= 3:
            self.setText(", ".join(gewaehlt))
        else:
            self.setText(f"{len(gewaehlt)} Gruppen")
        self.setToolTip("Mehrere Gruppen anhaken – angezeigt wird alles, was zu einer davon passt")

    def _melden(self) -> None:
        self._beschriften()
        self.geaendert.emit(self.auswahl())
