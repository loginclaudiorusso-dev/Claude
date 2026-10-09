"""Kalender-Raster im Stil von Outlook: Monat (6 Wochen) oder Woche, Termine als farbige Chips."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QToolTip, QWidget

from .. import termine as tm
from . import theme

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WT_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def art_farbe(art: str) -> QColor:
    t = theme.T
    k = t.kategorie
    return QColor({"anreise": k.get("Reha", t.accent), "uwt": k.get("UWT", t.ok), "abreise": k.get("Mieter", t.knapp),
                   "notiz": k.get("FRAI", t.accent), "eigen": t.accent}.get(art, t.text_3))


def wochenstart(d: date) -> date:
    return d - timedelta(days=d.weekday())


class KalenderRaster(QWidget):
    """Klick auf einen Tag → ``tag_geklickt``; Doppelklick auf einen Termin → ``termin_geoeffnet``."""

    tag_geklickt = Signal(object)
    termin_geoeffnet = Signal(object)

    KOPF = 30
    CHIP = 22

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.modus = "monat"
        self.bezug = date.today().replace(day=1)
        self.auswahl = date.today()
        self._nach_tag: dict[date, list[tm.Termin]] = {}
        self._treffer: list[tuple[QRectF, object]] = []
        self._hoehe()

    # ---- Daten ------------------------------------------------------------------------------

    def setzen(self, termine: list[tm.Termin]) -> None:
        self._nach_tag = {}
        for t in termine:
            self._nach_tag.setdefault(t.datum, []).append(t)
        for ts in self._nach_tag.values():
            ts.sort(key=lambda t: (t.erledigt, list(tm.ARTEN).index(t.art) if t.art in tm.ARTEN else 9, t.titel))
        self._hoehe()
        self.update()

    def anzeigen(self, modus: str, bezug: date) -> None:
        self.modus = modus
        self.bezug = bezug
        self._hoehe()
        self.update()

    def tage(self) -> list[date]:
        if self.modus == "woche":
            start = wochenstart(self.bezug)
            return [start + timedelta(days=i) for i in range(7)]
        start = wochenstart(self.bezug.replace(day=1))
        return [start + timedelta(days=i) for i in range(42)]

    def titel(self) -> str:
        monate = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
                  "November", "Dezember"]
        if self.modus == "woche":
            a = wochenstart(self.bezug)
            e = a + timedelta(days=6)
            return f"KW {a.isocalendar()[1]} · {a:%d.%m.} – {e:%d.%m.%Y}"
        return f"{monate[self.bezug.month - 1]} {self.bezug.year}"

    # ---- Geometrie --------------------------------------------------------------------------

    def _zeilen_hoehe(self) -> int:
        if self.modus == "woche":
            meiste = max((len(self._nach_tag.get(d, [])) for d in self.tage()), default=0)
            return max(320, 40 + meiste * (self._chip_hoehe() + 3) + 12)
        return 132

    def _chip_hoehe(self) -> int:
        return self.CHIP * 2 - 2 if self.modus == "woche" else self.CHIP   # Woche: zwei Zeilen Text

    def _hoehe(self) -> None:
        zeilen = 1 if self.modus == "woche" else 6
        self.setFixedHeight(self.KOPF + zeilen * self._zeilen_hoehe() + 1)

    def _zelle(self, i: int) -> QRectF:
        b = (self.width() - 1) / 7
        h = self._zeilen_hoehe()
        return QRectF((i % 7) * b, self.KOPF + (i // 7) * h, b, h)

    # ---- Zeichnen ---------------------------------------------------------------------------

    def paintEvent(self, _):
        t = theme.T
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        schrift = QFont(theme.schrift())
        schrift.setPixelSize(12)
        fett = QFont(schrift)
        fett.setBold(True)
        klein = QFont(schrift)
        klein.setPixelSize(11)
        fm = QFontMetrics(klein)
        heute = date.today()
        self._treffer = []
        breite = (self.width() - 1) / 7

        p.fillRect(QRectF(0, 0, self.width(), self.height()), QColor(t.surface))
        # Wochentage
        p.setFont(fett)
        for i in range(7):
            p.setPen(QColor(t.text_2 if i < 5 else t.text_3))
            r = QRectF(i * breite + 10, 0, breite - 12, self.KOPF)
            name = WOCHENTAGE[i] if breite > 110 else WT_KURZ[i]
            if self.modus == "woche":
                d = self.tage()[i]
                name = f"{WT_KURZ[i]} {d:%d.%m.}"
                if d == date.today():   # heute: Rahmen um die Überschrift, Schrift bleibt normal
                    tr = QRectF(r.left() - 6, 4, QFontMetrics(fett).horizontalAdvance(name) + 12, self.KOPF - 8)
                    p.save()
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(QColor(t.accent), 1.8))
                    p.drawRoundedRect(tr, 10, 10)
                    p.restore()
            p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, name)

        for i, d in enumerate(self.tage()):
            r = self._zelle(i)
            ausserhalb = self.modus == "monat" and d.month != self.bezug.month
            if d.weekday() >= 5 or ausserhalb:
                p.fillRect(r, QColor(t.surface_2))
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(t.border), 1))
            p.drawRect(r)
            if d == self.auswahl:       # Auswahl dezent umrandet, ohne Farbe
                p.setPen(QPen(QColor(t.text_3), 1.5))
                p.drawRect(r.adjusted(1, 1, -1, -1))
            self._treffer.append((r, d))
            # Tageszahl (heute als gefüllter Kreis)
            if self.modus == "monat":
                zahl = f"{d.day}" if d.day != 1 else f"{d.day}. {['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'][d.month - 1]}"
                zr = QRectF(r.left() + 6, r.top() + 5, 26 if d.day != 1 else 60, 22)
                p.setPen(QColor(t.text_3 if ausserhalb else t.text))
                p.setFont(fett if d.day == 1 else schrift)
                if d == heute:        # heute: nur ein Ring um die Zahl, Schrift bleibt normal
                    p.drawText(QRectF(zr.left(), zr.top(), 24, 24), Qt.AlignCenter, zahl)
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(QColor(t.accent), 1.8))
                    p.drawEllipse(QRectF(zr.left(), zr.top(), 24, 24))
                else:
                    p.drawText(QRectF(zr.left() + 3, zr.top(), zr.width(), 24), Qt.AlignVCenter | Qt.AlignLeft, zahl)
                y = r.top() + 32
            else:
                y = r.top() + 10
            # Termine als Chips
            ts = self._nach_tag.get(d, [])
            ch = self._chip_hoehe()
            platz = int((r.bottom() - y - 4) // (ch + 3))
            zeigen = ts if len(ts) <= platz else self._gebuendelt(d, ts, platz, heute)
            p.setFont(klein)
            for term in zeigen:
                cr = QRectF(r.left() + 4, y, r.width() - 8, ch)
                self._chip(p, cr, term, fm, heute)
                self._treffer.append((cr, term))
                y += ch + 3
            rest = len(ts) - sum(self._anzahl(x) for x in zeigen)
            if rest > 0:
                p.setPen(QColor(t.text_2))
                p.drawText(QRectF(r.left() + 8, y, r.width() - 12, 18), Qt.AlignVCenter | Qt.AlignLeft,
                           f"+ {rest} weitere")
        p.end()

    @staticmethod
    def _anzahl(t: tm.Termin) -> int:
        return t.vorlauf if t.id.startswith("sammel:") else 1

    def _gebuendelt(self, d: date, ts: list[tm.Termin], platz: int, heute: date) -> list[tm.Termin]:
        """Zu viele Termine für die Zelle: je Art zu einem Eintrag zusammenfassen („Notiz zur Anreise: 5“).
        Klick darauf öffnet die Tagesansicht mit allen Einträgen."""
        gruppen: dict[str, list[tm.Termin]] = {}
        for t in ts:
            gruppen.setdefault(t.art, []).append(t)
        eintraege = []
        for art, liste in gruppen.items():
            if len(liste) == 1:
                eintraege.append(liste[0])
                continue
            faellig = [x for x in liste if x.faellig(heute)]
            sammel = tm.Termin(f"sammel:{d.isoformat()}:{art}", d, f"{tm.ARTEN.get(art, art)}: {len(liste)}", "", art,
                               min(x.erinnern_am for x in faellig) if faellig else None,
                               all(x.erledigt for x in liste), vorlauf=len(liste))
            eintraege.append(sammel)
        return eintraege if len(eintraege) <= platz else eintraege[:max(platz - 1, 0)]

    def _chip(self, p: QPainter, r: QRectF, term: tm.Termin, fm: QFontMetrics, heute: date) -> None:
        t = theme.T
        farbe = art_farbe(term.art)
        fuellung = QColor(farbe)
        fuellung.setAlpha(40 if not term.erledigt else 18)
        p.setPen(Qt.NoPen)
        p.setBrush(fuellung)
        p.drawRoundedRect(r, 4, 4)
        p.setBrush(farbe)
        p.drawRoundedRect(QRectF(r.left(), r.top(), 4, r.height()), 2, 2)
        links = 9
        if term.faellig(heute):
            p.setBrush(QColor(t.ueber))
            p.drawEllipse(QRectF(r.left() + 9, r.center().y() - 3.5, 7, 7))
            links = 20
        elif term.erinnern_am is not None and not term.erledigt:
            p.setPen(QPen(farbe, 1.4))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QRectF(r.left() + 9, r.center().y() - 3.5, 7, 7))
            links = 20
        p.setPen(QColor(t.text_3 if term.erledigt else t.text))
        text = ("✓ " if term.erledigt else "") + term.titel
        breite = int(r.width() - links - 4)
        if r.height() > self.CHIP:        # zwei Zeilen: erste Zeile umbrechen, Rest kürzen
            zeilen, rest = [], text
            while rest and len(zeilen) < 2:
                n = len(rest)
                while n > 1 and fm.horizontalAdvance(rest[:n]) > breite:
                    n = rest.rfind(" ", 0, n - 1) if rest.rfind(" ", 0, n - 1) > 0 else n - 1
                zeilen.append(rest[:n] if len(zeilen) == 0 else fm.elidedText(rest, Qt.ElideRight, breite))
                rest = rest[n:].lstrip() if len(zeilen) == 1 else ""
            p.drawText(r.adjusted(links, 3, -4, -3), Qt.AlignTop | Qt.AlignLeft, "\n".join(zeilen))
        else:
            p.drawText(r.adjusted(links, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft,
                       fm.elidedText(text, Qt.ElideRight, breite))

    # ---- Interaktion ------------------------------------------------------------------------

    def _finde(self, pos) -> object | None:
        for r, obj in reversed(self._treffer):
            if r.contains(pos):
                return obj
        return None

    def mouseMoveEvent(self, e):
        obj = self._finde(e.position())
        self.setCursor(Qt.PointingHandCursor if obj is not None else Qt.ArrowCursor)
        if isinstance(obj, tm.Termin) and obj.id.startswith("sammel:"):
            QToolTip.showText(e.globalPosition().toPoint() + QPoint(12, 12),
                              f"<b>{obj.titel}</b><br>Klicken zeigt alle Einträge des Tages", self)
        elif isinstance(obj, tm.Termin):
            erin = ""
            if obj.erinnern_am is not None:
                erin = "<br>✓ erledigt" if obj.erledigt else f"<br>Erinnerung ab {obj.erinnern_am:%d.%m.%Y}"
            QToolTip.showText(e.globalPosition().toPoint() + QPoint(12, 12),
                              f"<b>{obj.titel}</b><br>{tm.ARTEN.get(obj.art, obj.art)} · {obj.datum:%d.%m.%Y}"
                              + (f"<br>{obj.text.replace(chr(10), '<br>')}" if obj.text else "") + erin, self)
        else:
            QToolTip.hideText()

    def mousePressEvent(self, e):
        obj = self._finde(e.position())
        if isinstance(obj, tm.Termin):
            obj = obj.datum
        if isinstance(obj, date):
            self.auswahl = obj
            self.update()
            self.tag_geklickt.emit(obj)

    def mouseDoubleClickEvent(self, e):
        obj = self._finde(e.position())
        if isinstance(obj, tm.Termin) and not obj.id.startswith("sammel:"):
            self.termin_geoeffnet.emit(obj)
