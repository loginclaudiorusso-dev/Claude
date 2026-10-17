"""Startseite mit zwei Ansichten:

* **Heute** (Standard): eine ruhige, priorisierte Vorgangsliste (``belegung/vorgaenge.py``) – je Vorgang eine Zeile
  mit genau einer Aktion, die direkt zur Bearbeitung führt; „Zuerst klären“, „Als Nächstes“, „Zur Info“ (eingeklappt).
* **Übersicht**: „Mein Dashboard“ – Kacheln selbst zusammenstellen – hinzufügen, entfernen, Breite wählen und per
Ziehen umordnen („Anpassen“ oben rechts). Die Anordnung wird gespeichert.

Die Kacheln zeigen, was heute zu tun ist (Zimmer, Anreisen, Abreisen, Reinigung, Erinnerungen …) und führen
mit einem Klick an die richtige Stelle.
"""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

from PySide6.QtCore import QMimeData, Qt, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ... import cockpit, eintragen
from ... import termine as tm
from ... import zimmerplan as zp
from ..basis import Seite, Zustand, sichtbar
from ..widgets import Karte, Pille, Segment, icon_setzen, knopf, label, leeren

MIME = "application/x-belegung-kachel"
WOTAG = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def theme_alpha_rand() -> str:
    from .. import theme

    return theme.alpha(theme.T.text_3, .25)


def _tag(d: date, heute: date) -> str:
    if d == heute:
        return "heute"
    if d == heute + timedelta(days=1):
        return "morgen"
    return f"{WOTAG[d.weekday()]} {d:%d.%m.}"


class Kachel(Karte):
    """Eine Kachel. Im Anpassen-Modus: Griff zum Ziehen, Breite ½/ganz, Entfernen; Ablegen auf einer anderen
    Kachel setzt sie davor."""

    verschoben = Signal(str, str)          # gezogene Kachel, Ziel (davor)

    def __init__(self, seite: "StartSeite", art: cockpit.KachelArt, breite: int):
        super().__init__(art.titel, None, abstand=16)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.seite, self.art, self.breite = seite, art, breite
        self.setProperty("kachel", True)
        self.leiste = QWidget()
        h = QHBoxLayout(self.leiste)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        griff = QLabel("⠿  ziehen")
        griff.setProperty("rolle", "klein")
        griff.setCursor(Qt.OpenHandCursor)
        griff.setToolTip("Kachel mit der Maus an eine andere Stelle ziehen")
        h.addWidget(griff)
        self.b_breite = knopf("Breiter" if breite == 1 else "Schmaler", "ghost", None,
                              "Ganze Breite" if breite == 1 else "Halbe Breite")
        self.b_breite.clicked.connect(lambda: seite.breite_wechseln(art.id))
        h.addWidget(self.b_breite)
        weg = knopf("", "ghost", "schliessen", "Kachel entfernen")
        weg.clicked.connect(lambda: seite.entfernen(art.id))
        h.addWidget(weg)
        self.aktion(self.leiste)
        self.leiste.setVisible(seite.bearbeiten)
        self.setAcceptDrops(True)
        self._start = None

    # ---- Ziehen und Ablegen ---------------------------------------------------------------

    def mousePressEvent(self, e) -> None:
        if self.seite.bearbeiten and e.button() == Qt.LeftButton:
            self._start = e.position().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        if self._start is None or not self.seite.bearbeiten:
            return super().mouseMoveEvent(e)
        if (e.position().toPoint() - self._start).manhattanLength() < 12:
            return
        self._start = None
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(MIME, self.art.id.encode())
        drag.setMimeData(mime)
        drag.setPixmap(self.grab().scaledToWidth(min(self.width(), 320), Qt.SmoothTransformation))
        drag.setHotSpot(e.position().toPoint() * (min(self.width(), 320) / max(self.width(), 1)))
        drag.exec(Qt.MoveAction)

    def mouseReleaseEvent(self, e) -> None:
        self._start = None
        super().mouseReleaseEvent(e)

    def dragEnterEvent(self, e) -> None:
        if self.seite.bearbeiten and e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()
            self._ziel(True)

    def dragLeaveEvent(self, e) -> None:
        self._ziel(False)

    def dropEvent(self, e) -> None:
        self._ziel(False)
        quelle = bytes(e.mimeData().data(MIME)).decode()
        e.acceptProposedAction()
        self.seite.verschieben(quelle, self.art.id)

    def _ziel(self, an: bool) -> None:
        self.setProperty("ablegen", an)
        self.style().unpolish(self)
        self.style().polish(self)


class Ablage(QLabel):
    """Ablagefläche am Ende („hierher ziehen = ans Ende“)."""

    def __init__(self, seite: "StartSeite"):
        super().__init__("Hierher ziehen, um eine Kachel ans Ende zu setzen")
        self.seite = seite
        self.setAlignment(Qt.AlignCenter)
        self.setProperty("ablage", True)
        self.setMinimumHeight(56)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()

    def dropEvent(self, e) -> None:
        e.acceptProposedAction()
        self.seite.verschieben(bytes(e.mimeData().data(MIME)).decode(), None)


class StartSeite(Seite):
    titel = "Start"
    untertitel = "Mein Dashboard – selbst zusammengestellt"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.bearbeiten = False
        self.kacheln = cockpit.anordnung()
        # Kopf: „Anpassen“ – im Anpassen-Modus zusätzlich „Kachel hinzufügen“ und „Standard“
        self.kopf_aktion = QWidget()
        h = QHBoxLayout(self.kopf_aktion)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.b_hinzu = knopf("Kachel hinzufügen", "ghost", "plus")
        self.m_hinzu = QMenu(self.b_hinzu)
        self.m_hinzu.aboutToShow.connect(self._hinzu_menue)
        self.b_hinzu.setMenu(self.m_hinzu)
        self.b_standard = knopf("Standard", "ghost", None, "Die vorgeschlagene Anordnung wiederherstellen")
        self.b_standard.clicked.connect(self._standard)
        self.b_anpassen = knopf("Anpassen", "ghost", "neu", "Kacheln hinzufügen, entfernen, Breite ändern und umordnen")
        self.b_anpassen.clicked.connect(self._anpassen)
        for b in (self.b_hinzu, self.b_standard, self.b_anpassen):
            h.addWidget(b)
        self.b_hinzu.setVisible(False)
        self.b_standard.setVisible(False)

        # Ansicht: „Heute“ (Vorgänge) oder „Übersicht“ (Kacheln) – wird gemerkt
        from ... import speicher

        self.ansicht = "kacheln" if speicher.einstellungen().get("start_ansicht") == "kacheln" else "heute"
        self.ansicht_wahl = Segment(["Heute", "Übersicht"], 1 if self.ansicht == "kacheln" else 0,
                                    tipps=["Was jetzt zu tun ist – nach Dringlichkeit, mit direktem Absprung",
                                           "Kacheln mit Kennzahlen und Listen – selbst zusammengestellt"])
        self.ansicht_wahl.geaendert.connect(self._ansicht_wechseln)
        self.lay.addWidget(self.ansicht_wahl, 0, Qt.AlignLeft)
        self.feed_w = QWidget()
        self.feed = QVBoxLayout(self.feed_w)
        self.feed.setContentsMargins(0, 0, 0, 0)
        self.feed.setSpacing(10)
        self.lay.addWidget(self.feed_w)
        self._info_offen = False
        self.hinweis = label("Anpassen: Kacheln an der Leiste „⠿ ziehen“ auf eine andere Kachel ziehen (wird davor "
                             "eingesetzt), Breite umschalten oder mit × entfernen. „Fertig“ speichert.", "klein",
                             umbruch=True)
        self.hinweis.setVisible(False)
        self.lay.addWidget(self.hinweis)
        # Titel und Untertitel der Seite (im Anpassen-Modus änderbar)
        self.titel, self.untertitel = cockpit.titel()
        self.titel_zeile = QWidget()
        tz = QHBoxLayout(self.titel_zeile)
        tz.setContentsMargins(0, 0, 0, 0)
        tz.setSpacing(8)
        self.e_titel = QLineEdit(self.titel)
        self.e_titel.setMaxLength(40)
        self.e_titel.setPlaceholderText(cockpit.TITEL_STANDARD[0])
        self.e_titel.setToolTip("Titel der Startseite (auch im Tab und in der Seitenleiste)")
        self.e_untertitel = QLineEdit(self.untertitel)
        self.e_untertitel.setMaxLength(80)
        self.e_untertitel.setPlaceholderText("Untertitel (leer = keiner)")
        tz.addWidget(label("Titel", "fett"))
        tz.addWidget(self.e_titel, 1)
        tz.addWidget(label("Untertitel", "fett"))
        tz.addWidget(self.e_untertitel, 2)
        self.titel_zeile.setVisible(False)
        self.lay.addWidget(self.titel_zeile)
        self.raster_w = QWidget()
        self.raster = QGridLayout(self.raster_w)
        self.raster.setContentsMargins(0, 0, 0, 0)
        self.raster.setHorizontalSpacing(16)
        self.raster.setVerticalSpacing(16)
        self.raster.setColumnStretch(0, 1)
        self.raster.setColumnStretch(1, 1)
        self.lay.addWidget(self.raster_w)
        self.lay.addStretch()
        for signal in (zustand.zimmer_geaendert, zustand.listen_geaendert, zustand.termine_geaendert):
            signal.connect(self.anstossen)

    # ---- läuft auch ohne Pivot-Datei --------------------------------------------------------

    def anstossen(self) -> None:
        self._veraltet = True
        if sichtbar(self):
            self._ausfuehren()

    def showEvent(self, e):
        QWidget.showEvent(self, e)
        if self._veraltet:
            self._ausfuehren()

    # ---- Anordnung --------------------------------------------------------------------------

    def _anpassen(self) -> None:
        self.bearbeiten = not self.bearbeiten
        self.b_anpassen.setText("Fertig" if self.bearbeiten else "Anpassen")
        self.b_anpassen.setProperty("variant", "primary" if self.bearbeiten else "ghost")
        self.b_anpassen.setProperty("icon_name", "haken" if self.bearbeiten else "neu")
        icon_setzen(self.b_anpassen)
        self.b_anpassen.style().unpolish(self.b_anpassen)
        self.b_anpassen.style().polish(self.b_anpassen)
        self.b_hinzu.setVisible(self.bearbeiten)
        self.b_standard.setVisible(self.bearbeiten)
        self.hinweis.setVisible(self.bearbeiten)
        self.titel_zeile.setVisible(self.bearbeiten)
        if not self.bearbeiten:
            cockpit.anordnung_speichern(self.kacheln)
            cockpit.titel_speichern(self.e_titel.text(), self.e_untertitel.text())
            self.titel, self.untertitel = cockpit.titel()
            self.e_titel.setText(self.titel)
            self.z.name_geaendert.emit()           # Seitenkopf, Tab und Seitenleiste übernehmen den Titel
            self.z.meldung.emit("Dashboard gespeichert.", "ok")
        self.aktualisieren()

    def _hinzu_menue(self) -> None:
        self.m_hinzu.clear()
        da = {k["id"] for k in self.kacheln}
        frei = [a for a in cockpit.KATALOG if a.id not in da]
        if not frei:
            self.m_hinzu.addAction("Alle Kacheln sind schon da").setEnabled(False)
        for a in frei:
            act = self.m_hinzu.addAction(f"{a.titel} – {a.beschreibung}", lambda i=a.id: self.hinzufuegen(i))
            act.setToolTip(a.beschreibung)

    def hinzufuegen(self, kid: str) -> None:
        if kid in cockpit.ARTEN and all(k["id"] != kid for k in self.kacheln):
            self.kacheln.append({"id": kid, "breite": cockpit.ARTEN[kid].breite})
            self._geaendert()

    def entfernen(self, kid: str) -> None:
        self.kacheln = [k for k in self.kacheln if k["id"] != kid]
        self._geaendert()

    def breite_wechseln(self, kid: str) -> None:
        for k in self.kacheln:
            if k["id"] == kid:
                k["breite"] = 1 if k.get("breite") == 2 else 2
        self._geaendert()

    def verschieben(self, kid: str, vor: str | None) -> None:
        self.kacheln = cockpit.verschieben(self.kacheln, kid, vor)
        self._geaendert()

    def _standard(self) -> None:
        self.kacheln = [{"id": i, "breite": cockpit.ARTEN[i].breite} for i in cockpit.STANDARD]
        self._geaendert()

    def _geaendert(self) -> None:
        cockpit.anordnung_speichern(self.kacheln)
        self.aktualisieren()

    # ---- Anzeige ----------------------------------------------------------------------------

    def aktualisieren(self) -> None:
        heute = date.today()
        try:
            self.stand = zp.laden()
        except Exception:                      # noqa: BLE001 – Startseite bleibt bedienbar
            self.stand = None
        heute_ansicht = self.ansicht == "heute" and not self.bearbeiten
        self.feed_w.setVisible(heute_ansicht)
        self.raster_w.setVisible(not heute_ansicht)
        self.b_anpassen.setVisible(not heute_ansicht)
        self.ansicht_wahl.setVisible(not self.bearbeiten)
        if heute_ansicht:
            self._heute_zeigen(heute)
            return
        while self.raster.count():
            item = self.raster.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._widgets: list[tuple[QWidget, int]] = []
        for k in self.kacheln:
            art = cockpit.ARTEN[k["id"]]
            breite = 2 if k.get("breite") == 2 else 1
            kachel = Kachel(self, art, breite)
            try:
                getattr(self, f"_k_{art.id}")(kachel, heute)
            except Exception:                  # noqa: BLE001 – eine kaputte Kachel darf die Seite nicht stören
                leeren(kachel.inhalt)
                kachel.inhalt.addWidget(label("Konnte nicht geladen werden.", "muted"))
            self._widgets.append((kachel, breite))
        if self.bearbeiten:
            self._widgets.append((Ablage(self), 2))
        if not self.kacheln and not self.bearbeiten:
            self._widgets.append((Karte("Noch keine Kacheln", "Oben rechts auf „Anpassen“ und dann „Kachel hinzufügen“."), 2))
        self._spalten = None
        self._anordnen()

    def _anordnen(self) -> None:
        """Zwei Spalten, im schmalen Fenster eine – halbe Kacheln stehen dann untereinander."""
        spalten = 2 if self.scroll.viewport().width() >= 1000 else 1
        if spalten == self._spalten:
            return
        self._spalten = spalten
        for w, _b in self._widgets:
            self.raster.removeWidget(w)
        self.raster.setColumnStretch(1, 1 if spalten == 2 else 0)
        zeile = spalte = 0
        for w, breite in self._widgets:
            breite = min(breite, spalten)
            if spalte + breite > spalten:
                zeile, spalte = zeile + 1, 0
            self.raster.addWidget(w, zeile, spalte, 1, breite if spalten == 2 else 1)
            spalte += breite
            if spalte >= spalten:
                zeile, spalte = zeile + 1, 0

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if getattr(self, "_widgets", None):
            self._anordnen()

    # ---- Ansicht „Heute“ ----------------------------------------------------------------------

    def _ansicht_wechseln(self, i: int) -> None:
        from ... import speicher

        self.ansicht = "kacheln" if i == 1 else "heute"
        speicher.einstellung_setzen("start_ansicht", self.ansicht)
        self.aktualisieren()

    def _heute_zeigen(self, heute: date) -> None:
        from ... import gebaeudeplan, mails, vorgaenge

        leeren(self.feed)
        try:
            liste = vorgaenge.sammeln(self.stand, heute, tm.alle(), mails.eingaenge(), mails.ARTEN,
                                      gebaeudeplan.neuer_plan_da())
        except Exception:                      # noqa: BLE001 – Startseite bleibt bedienbar
            liste = []
            self.feed.addWidget(label("Die Vorgänge konnten nicht vollständig geladen werden.", "muted"))
        anzahl = {s: sum(1 for v in liste if v.stufe == s) for s in vorgaenge.STUFEN}
        kopf = f"{WOTAG[heute.weekday()]} {heute:%d.%m.%Y}"
        if anzahl["dringend"]:
            kopf += f" · <b>{anzahl['dringend']} zuerst klären</b>"
        if anzahl["bald"]:
            kopf += f" · {anzahl['bald']} als Nächstes"
        self.feed.addWidget(label(kopf, "muted"))
        if not anzahl["dringend"] and not anzahl["bald"]:
            k = Karte("Alles erledigt", "Nichts Dringendes und nichts Offenes. Unten steht, was heute sonst ansteht.")
            self.feed.addWidget(k)
        for stufe in vorgaenge.STUFEN:
            teil = [v for v in liste if v.stufe == stufe]
            if not teil:
                continue
            if stufe == "info":
                b = QPushButton(f"{'▾' if self._info_offen else '▸'}  {vorgaenge.STUFE_TEXT[stufe]} ({len(teil)})")
                b.setProperty("variant", "zeile")
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(self._info_umschalten)
                self.feed.addWidget(b, 0, Qt.AlignLeft)
                if not self._info_offen:
                    continue
            else:
                self.feed.addWidget(label(vorgaenge.STUFE_TEXT[stufe], "abschnitt"))
            karte = Karte(abstand=4)
            for i, v in enumerate(teil):
                if i:
                    strich = QFrame()
                    strich.setFrameShape(QFrame.HLine)
                    strich.setStyleSheet(f"color: {theme_alpha_rand()};")
                    karte.inhalt.addWidget(strich)
                karte.inhalt.addWidget(self._vorgang_zeile(v))
            self.feed.addWidget(karte)

    def _info_umschalten(self) -> None:
        self._info_offen = not self._info_offen
        self._heute_zeigen(date.today())

    def _vorgang_zeile(self, v) -> QWidget:
        from .. import theme

        t = theme.T
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 6, 4, 6)
        h.setSpacing(12)
        farbe = {"dringend": t.ueber, "bald": t.knapp, "info": t.text_3}[v.stufe]
        punkt = QLabel("●")
        punkt.setStyleSheet(f"color: {farbe}; font-size: 10px;")
        h.addWidget(punkt, 0, Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(1)
        titel = label(escape(v.titel), "fett", umbruch=True)
        text.addWidget(titel)
        if v.detail:
            text.addWidget(label(escape(v.detail), "klein", umbruch=True))
        h.addLayout(text, 1)
        if v.erledigen:
            fertig = knopf("", "icon", "haken", "Erledigt – aus der Liste nehmen")
            fertig.clicked.connect(lambda _=False, tid=v.erledigen: self._termin_erledigt(tid))
            h.addWidget(fertig, 0, Qt.AlignVCenter)
        b = knopf(v.aktion, "primary" if v.stufe == "dringend" else "ghost")
        b.clicked.connect(lambda _=False, v=v: self._vorgang_oeffnen(v))
        h.addWidget(b, 0, Qt.AlignVCenter)
        return w

    def _gebaeudeplan_importieren(self) -> None:
        self.z.navigieren.emit("daten")
        seite = getattr(self.window(), "seiten", {}).get("daten")
        if seite is not None:
            seite.gebaeudeplan_importieren()

    def _termin_erledigt(self, tid: str) -> None:
        t = next((x for x in tm.alle() if x.id == tid), None)
        if t is not None:
            tm.erledigt_setzen(t, True)
            self.z.meldung.emit(f"Erledigt: {t.titel}", "ok")
            self.z.termine_geaendert.emit()

    def _vorgang_oeffnen(self, v) -> None:
        """Direkt dorthin, wo der Vorgang bearbeitet wird."""
        art, _, wert = v.ziel.partition(":")
        if art == "anreise":
            self._anreise(date.fromisoformat(wert))
        elif art == "konflikte":
            seite = self._zimmerplan("Aufgaben")
            if seite is not None:
                if seite.stand is None:
                    seite.neu_laden()
                seite._konflikte_loesen()
        elif art == "umzug":
            from ..umzug_dialog import umzug_oeffnen

            umzug_oeffnen(self, self.z, uid=wert)
        elif art == "person":
            from ..zimmerkarte import karte_oeffnen

            karte_oeffnen(self, self.z, person=wert)
        elif art in ("posteingang", "termine"):
            self.z.navigieren.emit(art)
        elif art == "maengel":
            seite = self._zimmerplan("Zimmer")
            if seite is not None:
                if seite.stand is None:
                    seite.neu_laden()
                seite.finder._zuruecksetzen()
                seite.finder.schnell["maengel"].setChecked(True)
                seite.finder._ansicht_setzen("liste")
        elif art == "gebaeudeplan":
            self._gebaeudeplan_importieren()
        else:
            self._zimmerplan({"eintragen": "Aufgaben", "engpaesse": "Aufgaben", "facility": "Aufgaben",
                              "reinigung": "Reinigung", "abreisen": "Abreisen"}.get(art, "Aufgaben"))

    # ---- Hilfen ----------------------------------------------------------------------------

    def _link(self, kachel: Kachel, text: str, aktion) -> None:
        b = knopf(text, "ghost")
        b.clicked.connect(aktion)
        kachel.inhalt.addWidget(b, 0, Qt.AlignLeft)

    def _zimmerplan(self, reiter: str | None = None):
        self.z.navigieren.emit("zimmerplan")
        fenster = self.window()
        seite = getattr(fenster, "seiten", {}).get("zimmerplan")
        if seite is not None and reiter:
            from .zimmerplan import TABS

            if reiter in TABS:
                seite.tabs.setzen(TABS.index(reiter), still=False)
        return seite

    def _zeile(self, kachel: Kachel, links: str, rechts: QWidget | None = None, aktion=None, tip: str = "") -> None:
        h = QHBoxLayout()
        h.setSpacing(8)
        if aktion is not None:
            b = QPushButton(links)
            b.setProperty("variant", "zeile")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(aktion)
            b.setToolTip(tip)
            h.addWidget(b, 1)
        else:
            lbl = label(links, umbruch=True)
            lbl.setTextFormat(Qt.RichText)
            lbl.setContentsMargins(8, 4, 0, 4)          # bündig mit den klickbaren Zeilen
            lbl.setToolTip(tip)
            h.addWidget(lbl, 1)
        if rechts is not None:
            h.addWidget(rechts, 0, Qt.AlignVCenter)
        kachel.inhalt.addLayout(h)

    # ---- Kacheln ----------------------------------------------------------------------------

    def _k_heute(self, k: Kachel, heute: date) -> None:
        if self.stand is None:
            k.inhalt.addWidget(label("Zimmerplan nicht verfügbar.", "muted"))
            return
        z = cockpit.zimmer_heute(self.stand, heute)
        raster = QGridLayout()
        raster.setHorizontalSpacing(18)
        for i, (wert, text, stufe) in enumerate(((z["frei"], "frei", "ok"), (z["belegt"], "belegt", "neutral"),
                                                 (z["gesperrt"], "gesperrt", "neutral"),
                                                 (z["ohne_zimmer"], "ohne Zimmer (8 Wo.)",
                                                  "knapp" if z["ohne_zimmer"] else "ok"))):
            w = label(str(wert), "kpi_wert")
            raster.addWidget(w, 0, i)
            raster.addWidget(Pille(text, stufe), 1, i, Qt.AlignLeft)
        k.inhalt.addLayout(raster)
        self._link(k, "Zimmer ansehen →", lambda: self._zimmerplan("Zimmer"))

    def _k_erinnerungen(self, k: Kachel, heute: date) -> None:
        offen = [t for t in tm.alle() if t.faellig(heute)]
        if not offen:
            k.inhalt.addWidget(label("Nichts fällig.", "muted"))
        for t in offen[:6]:
            erledigt = knopf("Erledigt", "ghost", "haken")
            erledigt.clicked.connect(lambda _=False, t=t: (tm.erledigt_setzen(t, True), self.z.termine_geaendert.emit()))
            oeffnen = None
            if t.person:
                oeffnen = (lambda _=False, t=t: self._person_oeffnen(t))
            self._zeile(k, f"{_tag(t.datum, heute)} · {t.titel}", erledigt, oeffnen, t.text)
        if len(offen) > 6:
            k.inhalt.addWidget(label(f"… und {len(offen) - 6} weitere", "klein"))
        self._link(k, "Alle Termine →", lambda: self.z.navigieren.emit("termine"))

    def _k_posteingang(self, k: Kachel, heute: date) -> None:
        from ... import mails

        offen = [x for x in mails.eingaenge() if x.status in ("offen", "zu prüfen")]
        if not offen:
            k.inhalt.addWidget(label("Nichts offen.", "muted"))
        for x in offen[:6]:
            rest = x.offen_zu_pruefen
            p = Pille(f"{len(rest)} offen" if rest else x.status, "kritisch" if rest else "knapp")
            p.setToolTip("Noch abzuhaken: " + ", ".join(rest) if rest else "Noch nicht bearbeitet")
            self._zeile(k, f"{mails.ARTEN.get(x.art, x.art)} · {x.name or x.betreff or '–'}", p,
                        lambda: self.z.navigieren.emit("posteingang"))
        self._link(k, "Zum Posteingang →", lambda: self.z.navigieren.emit("posteingang"))

    def _person_oeffnen(self, t: tm.Termin) -> None:
        from ..zimmerkarte import karte_oeffnen

        karte_oeffnen(self, self.z, person=t.person)

    def _k_anreisen(self, k: Kachel, heute: date) -> None:
        if self.stand is None:
            return
        tage = cockpit.anreisen(self.stand, heute)
        if not tage:
            k.inhalt.addWidget(label("Keine Anreisen in den nächsten 7 Tagen.", "muted"))
        for a in tage:
            fertig = a.mit_zimmer == a.personen
            p = Pille(f"{a.mit_zimmer}/{a.personen} mit Zimmer", "ok" if fertig else "knapp")
            self._zeile(k, f"{_tag(a.tag, heute)} · {a.text}", p, lambda _=False, a=a: self._anreise(a.tag),
                        "Im Zimmerplan zuteilen")

    def _anreise(self, tag: date) -> None:
        self.z.navigieren.emit("zimmerplan")
        seite = getattr(self.window(), "seiten", {}).get("zimmerplan")
        if seite is not None:
            seite.anreise_zeigen(tag)

    def _k_abreisen(self, k: Kachel, heute: date) -> None:
        if self.stand is None:
            return
        liste = cockpit.abreisen(self.stand, heute)
        if not liste:
            k.inhalt.addWidget(label("Heute und morgen reist niemand ab.", "muted"))
        for a in liste[:8]:
            self._zeile(k, f"{_tag(a.tag, heute)} · {a.name}", Pille(a.zimmer.removeprefix("GS-"), "neutral"),
                        lambda _=False, a=a: self._zimmer(a.zimmer), a.massnahme)
        if len(liste) > 8:
            k.inhalt.addWidget(label(f"… und {len(liste) - 8} weitere", "klein"))
        self._link(k, "Abreiseliste öffnen", lambda: self._zimmerplan("Abreisen"))

    def _zimmer(self, zid: str) -> None:
        from ..zimmerkarte import karte_oeffnen

        karte_oeffnen(self, self.z, zid)

    def _k_reinigung(self, k: Kachel, heute: date) -> None:
        if self.stand is None:
            return
        from ... import reinigungsliste as rl

        kon, offen = cockpit.reinigung_heute(self.stand, heute)
        if not kon and not offen:
            k.inhalt.addWidget(label("Heute ist nichts offen.", "muted"))
        for r in kon[:5]:
            self._zeile(k, f"<b>{escape(r.zimmer.kurz)}</b> · {escape(rl.konflikt_text(r))}", Pille("dringend", "ueber"),
                        tip="Noch nicht gereinigt, obwohl heute/morgen jemand einzieht")
        for r in offen[:max(0, 6 - len(kon))]:
            self._zeile(k, f"<b>{escape(r.zimmer.kurz)}</b> · {escape(r.art)} · sauber bis {escape(rl.frist_text(r))}")
        self._link(k, "Reinigungsliste →", lambda: self._zimmerplan("Reinigung"))

    def _k_eintragen(self, k: Kachel, heute: date) -> None:
        if self.stand is None:
            return
        zeilen = [z for z in eintragen.offen(self.stand.lage, heute, heute + timedelta(days=14)) if not z.haken]
        wert = label(str(len(zeilen)), "kpi_wert")
        k.inhalt.addWidget(wert)
        k.inhalt.addWidget(label("Buchungen für die nächsten 14 Tage noch im Belegungssystem eintragen"
                                 if zeilen else "Alles eingetragen.", "muted", umbruch=True))
        self._link(k, "Zu den Aufgaben →", lambda: self._zimmerplan("Aufgaben"))

    def _k_engpaesse(self, k: Kachel, heute: date) -> None:
        if self.stand is None:
            return
        erkl = "<br>".join(f"<b>{eintragen.ENGPASS_NAMEN[a]}:</b> {t}" for a, t in eintragen.ENGPASS_ERKLAERUNG.items())
        erkl += f"<br><b>Ampel:</b> {eintragen.grenzen_text()}"
        k.setToolTip(erkl)
        k.inhalt.addWidget(label("Zimmer, die die ganze Woche frei sind · EMR = Haus 2, 1.–2. OG · Doppel = ganz "
                                 "freie Doppelzimmer für UWT (Maus über die Kachel: genaue Erklärung)", "klein",
                                 umbruch=True))
        k.inhalt.addWidget(label("Nach Planung: auch Anreisen ohne Zimmer probeweise zugeteilt", "klein"))
        for _jetzt, w in eintragen.nach_planung(self.stand, heute, 5).wochen:
            rechts = QWidget()
            h = QHBoxLayout(rechts)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            for art, text in (("gesamt", f"{w.gesamt} frei"), ("emr", f"EMR {w.emr}"), ("doppel", f"Doppel {w.doppel}")):
                p = Pille(text, {"ok": "neutral", "knapp": "knapp", "kritisch": "ueber"}[w.stufe(art)])
                knapp, kritisch = w.grenzen[art]
                p.setToolTip(f"{eintragen.ENGPASS_NAMEN[art]}: {getattr(w, art)} – knapp unter {knapp}, "
                             f"kritisch unter {kritisch}")
                h.addWidget(p)
            self._zeile(k, w.text, rechts)
        self._link(k, "Alle 12 Wochen und Grenzen →", lambda: self._zimmerplan("Aufgaben"))

    def _k_facility(self, k: Kachel, heute: date) -> None:
        if self.stand is None:
            return
        checks = [c for c in eintragen.facility_checks(self.stand.lage, heute - timedelta(days=7),
                                                       heute + timedelta(days=14)) if not c.haken]
        if not checks:
            k.inhalt.addWidget(label("Keine offenen Facility-Checks.", "muted"))
        for c in checks[:6]:
            self._zeile(k, f"{_tag(c.bis, heute)} · Zimmer {c.zimmer.removeprefix('GS-')} · {c.monate} Monate",
                        aktion=lambda _=False, c=c: self._zimmer(c.zimmer), tip=c.text)
        self._link(k, "Zu den Aufgaben →", lambda: self._zimmerplan("Aufgaben"))

    def _k_notizen(self, k: Kachel, heute: date) -> None:
        notizen = tm.notizen()[:6]
        if not notizen:
            k.inhalt.addWidget(label("Noch keine Notizen – in der Zimmer- und Personenkarte anlegen.", "muted"))
        for n in notizen:
            rechts = Pille(f"WV {n.wiedervorlage:%d.%m.}", "knapp" if n.wiedervorlage <= heute else "neutral") \
                if n.wiedervorlage else None
            self._zeile(k, f"{escape(n.name)}: {escape(n.text)}", rechts,
                        lambda _=False, n=n: self._person_oeffnen(tm.Termin("", heute, "", person=n.person)),
                        f"Notiz vom {n.erstellt:%d.%m.%Y}")

    def _k_belegung(self, k: Kachel, heute: date) -> None:
        from ...konfig import STANDORT_LABEL, STANDORTE, ampel_stufe
        from ..widgets import prozent, zahl

        ds = self.z.ds
        if ds is None:
            k.inhalt.addWidget(label("Noch keine Pivot-Daten geladen (Aktualisieren unten links).", "muted"))
            return
        raster = QGridLayout()
        raster.setHorizontalSpacing(24)
        for i, s in enumerate(STANDORTE):
            auf = ds.aufschluesselung(s, ds.stichtag, self.z.brutto)
            raster.addWidget(label(STANDORT_LABEL[s], "kpi_label"), 0, i)
            raster.addWidget(label(zahl(auf.belegt), "kpi_wert"), 1, i)
            if auf.kapazitaet:
                stufe, text = ampel_stufe(auf.anteil)
                p = Pille(prozent(auf.anteil), stufe)
                p.setToolTip(text)
                raster.addWidget(p, 2, i, Qt.AlignLeft)
        k.inhalt.addLayout(raster)
        self._link(k, "Zur Übersicht →", lambda: self.z.navigieren.emit("uebersicht"))

    def _k_schnell(self, k: Kachel, heute: date) -> None:
        fenster = self.window()
        for text, icon, aktion in (
                ("Name oder Zimmer suchen", "personen", lambda: fenster.suchen() if hasattr(fenster, "suchen") else None),
                ("Person anlegen", "plus", self._person_anlegen),
                ("Gebäudeplan importieren", "hochladen", self._gebaeudeplan_importieren),
                ("Neuer Termin", "kalender", lambda: self.z.navigieren.emit("termine"))):
            b = knopf(text, "ghost", icon)
            b.clicked.connect(aktion)
            k.inhalt.addWidget(b, 0, Qt.AlignLeft)

    def _k_optimierung(self, k: Kachel, heute: date) -> None:
        k.inhalt.addWidget(label("Prüft alle Belegungen wie beim Zuteilen: Regelverstöße (z. B. lange Maßnahme auf "
                                 "Haus 2, 1. OG), bessere Zimmer und sinnvolle Tausche – jeweils mit Begründung, "
                                 "umgesetzt wird erst nach Bestätigung.", "muted", umbruch=True))
        b = knopf("Jetzt prüfen", "primary", "funke")
        b.clicked.connect(self._optimieren)
        k.inhalt.addWidget(b, 0, Qt.AlignLeft)

    def _optimieren(self) -> None:
        from ..optimieren import OptimierenDialog

        OptimierenDialog(self.z, self.window()).exec()

    def _person_anlegen(self) -> None:
        from ..dialoge import person_bearbeiten

        person_bearbeiten(self, self.z, None)
