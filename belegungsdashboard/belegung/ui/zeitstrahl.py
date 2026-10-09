"""Zeitstrahl: Zimmer als Zeilen, Tage als Spalten, Belegungen als Balken (wie im Belegungssystem)."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from .. import zimmerplan as zp
from . import theme

WT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def stil(art: str) -> tuple[QColor, QColor, QColor, bool, bool]:
    """(Füllung, Rand, Schrift, gestrichelt, schraffiert) je Balkenart – klar unterscheidbar:
    belegt türkis (voll), geplant blau (gestrichelt), Pivot lila, gesperrt rot schraffiert."""
    t = theme.T
    if art == "belegt":
        return QColor(t.accent), QColor(t.accent), QColor(t.accent_text), False, False
    if art == "geplant":
        blau = QColor(t.kategorie.get("Reha", "#2a78d6"))
        weich = QColor(blau)
        weich.setAlpha(55)
        return weich, blau, QColor(t.text), True, False
    if art == "pivot":
        lila = QColor(t.kategorie.get("FRAI", "#7a6fd6"))
        weich = QColor(lila)
        weich.setAlpha(80)
        return weich, lila, QColor(t.text), False, False
    rot = QColor(t.ueber)
    weich = QColor(rot)
    weich.setAlpha(30)
    return weich, rot, QColor(t.text_2), False, True


def balken_malen(p: QPainter, r: QRectF, art: str) -> QColor:
    """Zeichnet einen Balken der Art in r und gibt die Schriftfarbe zurück."""
    fuellung, rand, schrift, gestrichelt, schraffiert = stil(art)
    p.setBrush(QBrush(fuellung))
    pen = QPen(rand, 1.4)
    if gestrichelt:
        pen.setStyle(Qt.DashLine)
    p.setPen(pen)
    p.drawRoundedRect(r, 4, 4)
    if schraffiert:
        muster = QColor(rand)
        muster.setAlpha(110)
        p.setBrush(QBrush(muster, Qt.BDiagPattern))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r.adjusted(1, 1, -1, -1), 3, 3)
    return schrift


def muster(art: str, breite: int = 22, hoehe: int = 12) -> QPixmap:
    """Kleines Legendenmuster – gezeichnet wie im Zeitstrahl."""
    from PySide6.QtWidgets import QApplication

    dpr = QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
    pm = QPixmap(int(breite * dpr), int(hoehe * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    balken_malen(p, QRectF(1, 1, breite - 2, hoehe - 2), art)
    p.end()
    return pm


class Zeitstrahl(QWidget):
    """Zeichnet die von ``zimmerplan.zeitstrahl`` gelieferten Zeilen. Klick auf Zimmer oder Balken
    meldet die Zimmer-ID (``zimmer_geklickt``)."""

    zimmer_geklickt = Signal(str)
    verschieben = Signal(str, str, str)      # Person, von Zimmer, nach Zimmer (geplanten Balken gezogen)

    KOPF = 46        # Datumskopf
    LINKS = 118      # Spalte mit Zimmernummern
    SPUR = 26        # Höhe je Spur
    GRUPPE = 28      # Zwischenüberschrift Haus/Etage/Flur

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._zeilen: list[tuple[zp.Zimmer, list[list[zp.Balken]]]] = []
        self._von = self._bis = date.today()
        self._layout: list[tuple] = []     # (art, y, h, objekt)
        self.gruppen: set[str] = set()     # andere Gruppen blass zeichnen (Gruppenfilter „wohnt dort“)
        self.arten: set[str] = set()       # andere Arten blass zeichnen (Legende als Filter)
        self._treffer: list[tuple[QRectF, object]] = []
        self.verschiebbar = False          # geplante Balken per Ziehen in ein anderes Zimmer verschieben
        self._druck: tuple | None = None   # (Startpunkt, Zimmer-ID, Balken) beim Drücken auf einen geplanten Balken
        self._ziel: tuple | None = None    # (y, h, Zimmer) unter dem Mauszeiger beim Ziehen

    def setzen(self, zeilen, von: date, bis: date) -> None:
        self._zeilen, self._von, self._bis = zeilen, von, bis
        self._layout = []
        y = self.KOPF
        letzte = None
        for z, spuren in zeilen:
            schluessel = (z.haus, z.etage)
            if schluessel != letzte:
                self._layout.append(("gruppe", y, self.GRUPPE, zp.flur_text(z)))
                y += self.GRUPPE
                letzte = schluessel
            h = self.SPUR * max(len(spuren), 1) + 6
            self._layout.append(("zimmer", y, h, (z, spuren)))
            y += h
        self.setFixedHeight(max(y + 8, self.KOPF + 60))
        self.update()

    # ---- Geometrie ----------------------------------------------------------------------

    @property
    def _tage(self) -> int:
        return (self._bis - self._von).days + 1

    def _spalte(self) -> float:
        return max((self.width() - self.LINKS) / max(self._tage, 1), 6)

    def _x(self, d: date) -> float:
        return self.LINKS + (d - self._von).days * self._spalte()

    # ---- Zeichnen -----------------------------------------------------------------------

    def paintEvent(self, _):
        t = theme.T
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        schrift = QFont(theme.schrift())
        schrift.setPixelSize(12)
        klein = QFont(schrift)
        klein.setPixelSize(10)
        p.setFont(schrift)
        breite = self._spalte()
        heute = date.today()
        self._treffer = []

        # Wochenenden und heute als Hintergrund
        for i in range(self._tage):
            d = self._von + timedelta(days=i)
            x = self._x(d)
            if d.weekday() >= 5:
                p.fillRect(QRectF(x, self.KOPF, breite, self.height() - self.KOPF), QColor(t.surface_2))
            if d == heute:
                c = QColor(t.accent)
                c.setAlpha(28)
                p.fillRect(QRectF(x, 0, breite, self.height()), c)
        # Kopf: Tag + Wochentag – bei schmalen Spalten nur Montage und Monatsanfänge beschriften
        eng = breite < 22
        monate = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
        for i in range(self._tage):
            d = self._von + timedelta(days=i)
            x = self._x(d)
            if d == heute:
                p.fillRect(QRectF(x + 2, self.KOPF - 3, max(breite - 4, 2), 3), QColor(t.accent))
            if eng:
                if d.day == 1 or (i == 0 and d.day <= 20):
                    p.setFont(klein)
                    p.setPen(QColor(t.text_2))
                    p.drawText(QRectF(x + 2, 4, 60, 14), Qt.AlignLeft | Qt.AlignVCenter, f"{monate[d.month - 1]} {d.year}")
                if d.weekday() == 0 or d == heute:
                    p.setFont(schrift)
                    p.setPen(QColor(t.accent if d == heute else t.text))
                    p.drawText(QRectF(x - 8, 20, breite + 16, 18), Qt.AlignCenter, f"{d.day:02d}")
                continue
            p.setPen(QColor(t.accent if d == heute else t.text))
            p.setFont(schrift)
            p.drawText(QRectF(x, 6, breite, 18), Qt.AlignCenter, f"{d.day:02d}")
            p.setFont(klein)
            p.setPen(QColor(t.accent if d == heute else t.text_3))
            p.drawText(QRectF(x, 24, breite, 14), Qt.AlignCenter, WT[d.weekday()])
        # senkrechte Linien
        p.setPen(QPen(QColor(t.border), 1))
        for i in range(self._tage + 1):
            x = self.LINKS + i * breite
            p.drawLine(int(x), self.KOPF, int(x), self.height())
        p.drawLine(0, self.KOPF, self.width(), self.KOPF)

        fm = QFontMetrics(schrift)
        for art, y, h, obj in self._layout:
            if art == "gruppe":
                p.fillRect(QRectF(0, y, self.width(), h), QColor(t.surface_2))
                p.setPen(QColor(t.text_2))
                f = QFont(schrift)
                f.setBold(True)
                p.setFont(f)
                p.drawText(QRectF(10, y, self.width(), h), Qt.AlignVCenter | Qt.AlignLeft, obj)
                continue
            z, spuren = obj
            p.setPen(QPen(QColor(t.border), 1))
            p.drawLine(0, int(y + h), self.width(), int(y + h))
            p.setFont(schrift)
            p.setPen(QColor(t.text))
            merk = "".join(k for k, an in (("D", z.betten > 1), ("T", z.tiere), ("M", z.nur_maenner), ("G", z.gaeste)) if an)
            p.drawText(QRectF(12, y, self.LINKS - 16, h), Qt.AlignVCenter | Qt.AlignLeft, z.nr)
            if merk:
                p.setFont(klein)
                p.setPen(QColor(t.text_3))
                p.drawText(QRectF(12, y, self.LINKS - 18, h), Qt.AlignVCenter | Qt.AlignRight, merk)
                p.setFont(schrift)
            self._treffer.append((QRectF(0, y, self.LINKS, h), z.id))
            for s, spur in enumerate(spuren):
                for bk in spur:
                    x1 = self._x(bk.von) + 1
                    x2 = self._x(bk.bis) + breite - 1
                    r = QRectF(x1, y + 3 + s * self.SPUR, max(x2 - x1, 4), self.SPUR - 4)
                    blass = ((bool(self.gruppen) and bk.art != "gesperrt"
                              and zp.belegung_gruppe(bk.belegung) not in self.gruppen)
                             or (bool(self.arten) and bk.art not in self.arten))
                    p.setOpacity(0.3 if blass else 1.0)
                    schrift_farbe = balken_malen(p, r, bk.art)
                    p.setPen(schrift_farbe)
                    text = fm.elidedText(bk.text, Qt.ElideRight, int(r.width() - 10))
                    p.drawText(r.adjusted(6, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, text)
                    p.setOpacity(1.0)
                    self._treffer.append((r, (z.id, bk)))
        # Ziehen: Zielzeile hervorheben und den Balken dort als Vorschau zeichnen
        if self._druck is not None and self._ziel is not None:
            y, h, z = self._ziel
            _start, von_zid, bk = self._druck
            c = QColor(t.accent if z.id != von_zid else t.text_3)
            c.setAlpha(40)
            p.fillRect(QRectF(0, y, self.width(), h), c)
            r = QRectF(self._x(bk.von) + 1, y + 3, max(self._x(bk.bis) + breite - self._x(bk.von) - 2, 4), self.SPUR - 4)
            p.setOpacity(0.75)
            p.setPen(balken_malen(p, r, "geplant"))
            p.drawText(r.adjusted(6, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft,
                       fm.elidedText(f"→ {z.kurz}: {bk.text}", Qt.ElideRight, int(r.width() - 10)))
            p.setOpacity(1.0)
        p.end()

    # ---- Interaktion --------------------------------------------------------------------

    def _finde(self, pos) -> object | None:
        for r, obj in reversed(self._treffer):
            if r.contains(pos):
                return obj
        return None

    def _zeile(self, y: float):
        for art, zy, h, obj in self._layout:
            if art == "zimmer" and zy <= y < zy + h:
                return zy, h, obj[0]
        return None

    def mouseMoveEvent(self, e):
        if self._druck is not None:
            start = self._druck[0]
            if self._ziel is not None or (e.position() - start).manhattanLength() > 6:
                self._ziel = self._zeile(e.position().y())
                self.setCursor(Qt.ClosedHandCursor)
                QToolTip.hideText()
                self.update()
                return
        obj = self._finde(e.position())
        self.setCursor(Qt.PointingHandCursor if obj else Qt.ArrowCursor)
        if isinstance(obj, tuple):
            _zid, bk = obj
            b = bk.belegung
            ziehbar = self.verschiebbar and bk.art == "geplant" and b.person
            if ziehbar:
                self.setCursor(Qt.OpenHandCursor)
            QToolTip.showText(e.globalPosition().toPoint() + QPoint(12, 12),
                              f"<b>{bk.text}</b><br>{b.von:%d.%m.%Y} – {b.bis:%d.%m.%Y} "
                              f"({(b.bis - b.von).days + 1} Tage)"
                              + ("<br><i>Zum Verschieben in ein anderes Zimmer ziehen</i>" if ziehbar else ""), self)
        else:
            QToolTip.hideText()

    def mousePressEvent(self, e):
        obj = self._finde(e.position())
        if (self.verschiebbar and e.button() == Qt.LeftButton and isinstance(obj, tuple)
                and obj[1].art == "geplant" and obj[1].belegung.person):
            self._druck, self._ziel = (e.position(), obj[0], obj[1]), None   # Klick oder Ziehen – entscheidet das Loslassen
            return
        if obj is not None:
            self.zimmer_geklickt.emit(obj[0] if isinstance(obj, tuple) else obj)

    def mouseReleaseEvent(self, e):
        if self._druck is None:
            return
        _start, von_zid, bk = self._druck
        ziel = self._ziel
        self._druck = self._ziel = None
        self.setCursor(Qt.ArrowCursor)
        self.update()
        if ziel is None:                       # nicht gezogen → wie ein Klick
            self.zimmer_geklickt.emit(von_zid)
        elif ziel[2].id != von_zid:
            self.verschieben.emit(bk.belegung.person, von_zid, ziel[2].id)
