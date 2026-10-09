"""Terminkalender: fällige Erinnerungen, anstehende Termine, Monatsansicht und Einstellungen."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QComboBox, QFormLayout, QHBoxLayout, QSpinBox, QVBoxLayout, QWidget,
)

from ... import anreiseliste, autostart
from ... import termine as tm
from ... import zimmerplan as zp
from .. import theme
from ..basis import Seite, Zustand
from ..kalender import KalenderRaster, art_farbe
from ..widgets import Hinweis, Karte, Leer, Pille, Segment, Tabelle, knopf, label, leeren

WOCHENTAGE = tm.WOCHENTAGE
ZEITRAUM = [("4 Wochen", 28), ("3 Monate", 91), ("12 Monate", 365)]
ART_FILTER = [("Alle", None), ("Mit Erinnerung", "erinnerung"), ("Notizen zur Anreise", "notiz"), ("Abreisen", "abreise"),
              ("Anreisen", "anreise"), ("UWT", "uwt"), ("Eigene Termine", "eigen")]


def _tag(d: date) -> str:
    return f"{WOCHENTAGE[d.weekday()]} {d:%d.%m.%Y}"


class TermineSeite(Seite):
    titel = "Termine"
    untertitel = "Erinnerungen an Anreise-Notizen, Abreisen und eigene Termine – ohne Outlook"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.termine: list[tm.Termin] = []
        self._tabelle_termine: list[tm.Termin] = []
        zustand.listen_geaendert.connect(self.anstossen)
        zustand.termine_geaendert.connect(self.anstossen)

        kopf = QHBoxLayout()
        kopf.setSpacing(10)
        self.tabs = Segment(["Kalender", "Liste", "Einstellungen"], 0)
        self.tabs.geaendert.connect(self._tab)
        kopf.addWidget(self.tabs)
        kopf.addStretch()
        neu = knopf("Neuer Termin", "primary", "plus", "Eigenen Termin mit Erinnerung anlegen")
        neu.clicked.connect(lambda: self._eigener())
        kopf.addWidget(neu)
        self.lay.addLayout(kopf)
        self.kennzahlen = QHBoxLayout()           # Kennzahlen in eigener Zeile – übersichtlicher
        self.kennzahlen.setSpacing(8)
        self.lay.addLayout(self.kennzahlen)
        # „Rückgängig“ nach einem versehentlichen Erledigt
        self._zuletzt: tm.Termin | None = None
        self.rueck = QVBoxLayout()
        self.lay.addLayout(self.rueck)
        self._tag_dialog = None

        # fällige Erinnerungen – immer oben, solange etwas offen ist
        self.faellig_karte = Karte("Jetzt erinnern", "Kommt jeden Tag wieder, bis es abgehakt ist")
        self.faellig_liste = QVBoxLayout()
        self.faellig_liste.setSpacing(8)
        self.faellig_karte.inhalt.addLayout(self.faellig_liste)
        self.lay.addWidget(self.faellig_karte)

        self.seiten = [self._kalender_bauen(), self._anstehend_bauen(), self._einstellungen_bauen()]
        for w in self.seiten:
            self.lay.addWidget(w)
        self.lay.addStretch()
        self._tab(0)

    # ---- Signale wie Zimmerplan: läuft auch ohne geladene Pivot ----------------------------

    def anstossen(self) -> None:
        self._veraltet = True
        if self.isVisible():
            self._ausfuehren()

    def showEvent(self, e):
        QWidget.showEvent(self, e)
        if self._veraltet:
            self._ausfuehren()

    def _tab(self, i: int) -> None:
        for j, w in enumerate(self.seiten):
            w.setVisible(i == j)

    # ================================================================== Aufbau

    def _anstehend_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        filter_ = QHBoxLayout()
        filter_.setSpacing(10)
        self.f_art = QComboBox()
        for text, k in ART_FILTER:
            self.f_art.addItem(text, k)
        self.f_zeit = QComboBox()
        for text, tage in ZEITRAUM:
            self.f_zeit.addItem(text, tage)
        self.f_erledigt = QCheckBox("Erledigte zeigen")
        for x in (self.f_art, self.f_zeit):
            x.currentIndexChanged.connect(self._tabelle_fuellen)
            filter_.addWidget(x)
        self.f_erledigt.toggled.connect(self._tabelle_fuellen)
        filter_.addWidget(self.f_erledigt)
        filter_.addStretch()
        v.addLayout(filter_)
        self.tab = Tabelle(["Datum", "Was", "Erinnern ab", "Status"], ["l", "l", "l", "l"], dehnen=1)
        self.tab.setTextElideMode(Qt.ElideRight)
        self.tab.itemSelectionChanged.connect(self._auswahl)
        self.tab.doubleClicked.connect(lambda _i: self._bearbeiten())
        v.addWidget(self.tab)
        self.leer = Leer("kalender", "Keine Termine im Zeitraum",
                         "Notizen aus den Anreiselisten, Abreisen mit Erinnerung und eigene Termine erscheinen hier.")
        v.addWidget(self.leer)
        knoepfe = QHBoxLayout()
        knoepfe.setSpacing(8)
        self.b_erledigt = knopf("Erledigt", "primary", "haken")
        self.b_erledigt.clicked.connect(self._erledigt_umschalten)
        self.b_bearbeiten = knopf("Bearbeiten", "ghost")
        self.b_bearbeiten.clicked.connect(self._bearbeiten)
        for b in (self.b_erledigt, self.b_bearbeiten):
            knoepfe.addWidget(b)
        knoepfe.addStretch()
        v.addLayout(knoepfe)
        return w

    def _kalender_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        nav = QHBoxLayout()
        nav.setSpacing(6)
        zurueck = knopf("", "ghost", "links", "Zurück")
        zurueck.clicked.connect(lambda: self._blaettern(-1))
        heute = knopf("Heute", "ghost")
        heute.clicked.connect(self._heute)
        vor = knopf("", "ghost", "rechts", "Weiter")
        vor.clicked.connect(lambda: self._blaettern(1))
        for b in (zurueck, heute, vor):
            nav.addWidget(b)
        self.k_titel = label("", "kartentitel")
        nav.addSpacing(8)
        nav.addWidget(self.k_titel)
        nav.addStretch()
        self.k_modus = Segment(["Monat", "Woche"], 0)
        self.k_modus.geaendert.connect(lambda _i: self._kalender_zeigen())
        nav.addWidget(self.k_modus)
        v.addLayout(nav)

        rahmen = Karte(abstand=1)
        self.raster = KalenderRaster()
        self.raster.tag_geklickt.connect(self._tag_oeffnen)          # Klick auf einen Tag → Tagesansicht
        self.raster.termin_geoeffnet.connect(self._oeffnen)
        rahmen.inhalt.addWidget(self.raster)
        v.addWidget(rahmen)

        self.legende = label("", "klein", umbruch=True)
        self.legende.setTextFormat(Qt.RichText)
        v.addWidget(self.legende)
        return w

    def _einstellungen_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        e = tm.einstellungen()
        k = Karte("Erinnerungen", "Wann das Dashboard erinnert")
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.s_notiz = QSpinBox()
        self.s_notiz.setRange(0, 30)
        self.s_notiz.setSuffix(" Tage vor der Anreise")
        self.s_notiz.setSpecialValueText("am Anreisetag")
        self.s_notiz.setValue(e["notiz_tage"])
        self.s_notiz.setFixedWidth(230)
        self.s_notiz.valueChanged.connect(lambda n: (tm.einstellung_setzen(notiz_tage=n), self.anstossen()))
        form.addRow("Notizen zur Anreise", self.s_notiz)
        for schluessel, text in (("abreise_tage_emr", "Abreisen EMR"), ("abreise_tage", "Abreisen alle anderen")):
            sp = QSpinBox()
            sp.setRange(-1, 30)
            sp.setSpecialValueText("keine Erinnerung")
            sp.setSuffix(" Tage vorher")
            sp.setValue(e[schluessel])
            sp.setFixedWidth(230)
            sp.valueChanged.connect(lambda n, k=schluessel: (tm.einstellung_setzen(**{k: n}), self.anstossen(),
                                                              self.z.termine_geaendert.emit()))
            form.addRow(text, sp)
        k.inhalt.addLayout(form)
        k.inhalt.addWidget(label("Abreisen werden je Tag zu einer Erinnerung zusammengefasst (z. B. „Abreise: 7 Personen "
                                 "(EMR ASS)“); „alle anderen“ gilt auch für UWT-Blöcke. Wer eine eigene Erinnerung hat "
                                 "(Stift unter Daten & Import → Anreisen), wird einzeln erinnert.", "klein", umbruch=True))
        v.addWidget(k)

        h = Karte("Benachrichtigung", "Damit Erinnerungen auch kommen, wenn das Fenster zu ist")
        self.s_hintergrund = QCheckBox("Beim Schließen im Infobereich (unten rechts) weiterlaufen")
        self.s_hintergrund.setChecked(e["hintergrund"])
        self.s_hintergrund.toggled.connect(lambda an: tm.einstellung_setzen(hintergrund=an))
        h.inhalt.addWidget(self.s_hintergrund)
        self.s_autostart = QCheckBox("Mit Windows starten (unsichtbar im Infobereich)")
        self.s_autostart.setChecked(autostart.aktiv())
        self.s_autostart.setEnabled(autostart.moeglich())
        self.s_autostart.toggled.connect(self._autostart)
        h.inhalt.addWidget(self.s_autostart)
        if not autostart.moeglich():
            h.inhalt.addWidget(Hinweis("Autostart gibt es nur unter Windows.", "info"))
        h.inhalt.addWidget(label("Fällige Erinnerungen erscheinen als Windows-Benachrichtigung beim Start und danach "
                                 "alle 15 Minuten, sobald eine neue fällig wird – einmal am Tag je Erinnerung.",
                                 "klein", umbruch=True))
        test = knopf("Test-Benachrichtigung", "ghost", "glocke")
        test.clicked.connect(lambda: self.window().benachrichtigen("Belegungsdashboard",
                                                                    "So sehen Erinnerungen aus.")
                             if hasattr(self.window(), "benachrichtigen") else None)
        h.inhalt.addWidget(test, 0, Qt.AlignLeft)
        v.addWidget(h)
        return w

    # ================================================================== Inhalt

    def aktualisieren(self) -> None:
        self.termine = tm.alle()
        heute = date.today()
        faellig = [t for t in self.termine if t.faellig(heute)]
        woche = [t for t in self.termine if heute <= t.datum <= heute + timedelta(days=6) and t.art != "anreise"]
        leeren(self.kennzahlen)
        for text, stufe, tip in ((f"{len(faellig)} fällig", "knapp" if faellig else "ok", "Offene Erinnerungen"),
                                 (f"{len(woche)} diese Woche", "neutral", "Termine der nächsten 7 Tage")):
            p = Pille(text, stufe)
            p.setToolTip(tip)
            self.kennzahlen.addWidget(p)
        self.kennzahlen.addStretch()
        self._rueck_zeigen()
        self._faellige_zeigen(faellig)
        self._tabelle_fuellen()
        self._legende_zeigen()
        self._kalender_zeigen()
        self._tag_zeigen()

    def _zeile(self, t: tm.Termin, mit_datum: bool = True) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        if mit_datum:
            p = Pille(_tag(t.datum), "knapp" if t.datum <= date.today() + timedelta(days=1) else "neutral")
            h.addWidget(p, 0, Qt.AlignTop)
        art = label(tm.ARTEN.get(t.art, t.art), "klein")
        art.setMinimumWidth(110)
        h.addWidget(art, 0, Qt.AlignTop)
        text = label(f"<b>{t.titel}</b>" + (f"<br>{t.text.replace(chr(10), '<br>')}" if t.text else ""), umbruch=True)
        text.setTextFormat(Qt.RichText)
        h.addWidget(text, 1)
        if t.art == "eigen" or (t.art in ("notiz", "abreise") and t.person):
            o = knopf("Öffnen", "ghost")
            o.setToolTip("Eigenen Termin bearbeiten bzw. die Person (Notiz, Abreise) öffnen")
            o.clicked.connect(lambda _=False, t=t: self._oeffnen(t))
            h.addWidget(o, 0, Qt.AlignTop)
        if t.erinnern_am is not None:
            b = knopf("Wieder offen" if t.erledigt else "Erledigt", "ghost" if t.erledigt else "primary",
                      None if t.erledigt else "haken")
            b.clicked.connect(lambda _=False, t=t: self._erledigt(t, not t.erledigt))
            h.addWidget(b, 0, Qt.AlignTop)
        return w

    def _rueck_zeigen(self) -> None:
        leeren(self.rueck)
        t = self._zuletzt
        if t is None:
            return
        h = Hinweis(f"„{t.titel}“ als erledigt markiert.", "info", "Rückgängig")
        h.knopf.clicked.connect(lambda: self._rueckgaengig(t))
        self.rueck.addWidget(h)

    def _rueckgaengig(self, t: tm.Termin) -> None:
        self._zuletzt = None
        tm.erledigt_setzen(t, False)
        self.z.meldung.emit("Wieder offen.", "ok")
        self.z.termine_geaendert.emit()

    def _faellige_zeigen(self, faellig: list[tm.Termin]) -> None:
        leeren(self.faellig_liste)
        self.faellig_karte.setVisible(bool(faellig))
        for t in faellig:
            self.faellig_liste.addWidget(self._zeile(t))

    def _gefiltert(self) -> list[tm.Termin]:
        heute = date.today()
        art = self.f_art.currentData()
        bis = heute + timedelta(days=self.f_zeit.currentData() or 28)
        zeigen_erledigt = self.f_erledigt.isChecked()
        ergebnis = []
        for t in self.termine:
            if not (heute - timedelta(days=tm.RUECKBLICK) <= t.datum <= bis):
                continue
            if t.datum < heute and t.erinnern_am is None:
                continue
            if t.erledigt and not zeigen_erledigt:
                continue
            if art == "erinnerung" and t.erinnern_am is None:
                continue
            if art not in (None, "erinnerung") and t.art != art:
                continue
            ergebnis.append(t)
        return ergebnis

    def _tabelle_fuellen(self, *_):
        heute = date.today()
        self._tabelle_termine = self._gefiltert()
        zeilen, farben = [], {}
        t_ = theme.T
        for r, t in enumerate(self._tabelle_termine):
            if t.erinnern_am is None:
                status = ""
            elif t.erledigt:
                status = "✓ erledigt"
            elif t.faellig(heute):
                status = "fällig"
                farben[(r, 3)] = t_.knapp
            else:
                status = "geplant"
            zeilen.append([_tag(t.datum), t.titel, f"{t.erinnern_am:%d.%m.%Y}" if t.erinnern_am else "–", status])
            if t.datum == heute:
                farben[(r, 0)] = t_.accent
        self.tab.fuellen(zeilen, farben)
        for r, t in enumerate(self._tabelle_termine):
            if self.tab.item(r, 1):
                self.tab.item(r, 1).setToolTip(f"{tm.ARTEN.get(t.art, t.art)}\n{t.titel}\n{t.text}")
        self.tab.hoehe_anpassen(16)
        self.tab.setVisible(bool(zeilen))
        self.leer.setVisible(not zeilen)
        self._auswahl()

    def _gewaehlt(self) -> tm.Termin | None:
        zeilen = self.tab.selectionModel().selectedRows() if self.tab.selectionModel() else []
        if not zeilen or zeilen[0].row() >= len(self._tabelle_termine):
            return None
        return self._tabelle_termine[zeilen[0].row()]

    def _auswahl(self) -> None:
        t = self._gewaehlt()
        self.b_erledigt.setEnabled(t is not None and t.erinnern_am is not None)
        self.b_erledigt.setText("Wieder offen" if t is not None and t.erledigt else "Erledigt")
        self.b_bearbeiten.setEnabled(t is not None and t.art in ("eigen", "notiz", "abreise"))
        self.b_bearbeiten.setToolTip("Eigene Termine ändern, bei Notizen/Abreisen die Person öffnen")

    # ---- Kalender ---------------------------------------------------------------------------

    def _kalender_zeigen(self) -> None:
        modus = "woche" if self.k_modus.index() == 1 else "monat"
        bezug = self.raster.auswahl if modus == "woche" else self.raster.auswahl.replace(day=1)
        self.raster.anzeigen(modus, bezug)
        self.raster.setzen(self.termine)
        self.k_titel.setText(self.raster.titel())

    def _blaettern(self, richtung: int) -> None:
        a = self.raster.auswahl
        if self.k_modus.index() == 1:
            neu = a + timedelta(days=7 * richtung)
        else:
            m = a.month - 1 + richtung
            neu = date(a.year + m // 12, m % 12 + 1, 1)
        self.raster.auswahl = neu
        self._kalender_zeigen()
        self._tag_zeigen()

    def _heute(self) -> None:
        self.raster.auswahl = date.today()
        self._kalender_zeigen()
        self._tag_zeigen()

    def _legende_zeigen(self) -> None:
        teile = [f'<span style="color:{art_farbe(art).name()}">■</span>&nbsp;{text}' for art, text in tm.ARTEN.items()]
        self.legende.setText(" &nbsp; ".join(teile) + " &nbsp;·&nbsp; roter Punkt = fällig, Ring = Erinnerung geplant"
                             " · Doppelklick auf einen Termin öffnet ihn")

    def _tag_zeigen(self) -> None:
        """Offene Tagesansicht nach Änderungen auffrischen."""
        if self._tag_dialog is not None and self._tag_dialog.isVisible():
            self._tag_dialog.fuellen()

    def _tag_oeffnen(self, d: date) -> None:
        self._tag_dialog = TagDialog(self, d)
        self._tag_dialog.exec()
        self._tag_dialog = None

    def _oeffnen(self, t: tm.Termin) -> None:
        if t.art == "eigen":
            self._eigener(t)
        elif t.art in ("notiz", "abreise"):
            self._person_oeffnen(t.person)

    # ================================================================== Aktionen

    def _erledigt(self, t: tm.Termin, erledigt: bool) -> None:
        tm.erledigt_setzen(t, erledigt)
        self._zuletzt = t if erledigt else None
        self.z.termine_geaendert.emit()

    def _erledigt_umschalten(self) -> None:
        t = self._gewaehlt()
        if t is not None:
            self._erledigt(t, not t.erledigt)

    def _bearbeiten(self) -> None:
        t = self._gewaehlt()
        if t is None:
            return
        self._oeffnen(t)

    def _person_oeffnen(self, schluessel: str) -> None:
        from ..dialoge import PersonDialog, erinnerung_abgleichen

        personen, _ = anreiseliste.laden()
        p = next((p for p in personen if p.schluessel == schluessel), None)
        if p is None:
            return
        dialog = PersonDialog(p, self)
        if not dialog.exec():
            return
        neu = dialog.ergebnis
        meldung = erinnerung_abgleichen(p, neu)
        if neu is None:
            anreiseliste.person_loeschen(p.schluessel)
            zp.person_geloescht(p.schluessel)          # sonst blockiert die alte Zuweisung das Zimmer
            self.z.meldung.emit(f"{p.name} entfernt.", "ok")
        else:
            anreiseliste.person_speichern(neu, p.schluessel)
            zp.person_umbenannt(p.schluessel, neu.schluessel)
            self.z.meldung.emit(*(meldung or ("Gespeichert.", "ok")))
        self.z.listen_geaendert.emit()
        self.z.termine_geaendert.emit()

    def _eigener(self, t: tm.Termin | None = None, datum: date | None = None) -> None:
        from ..dialoge import TerminDialog

        dialog = TerminDialog(t, self, datum)
        if not dialog.exec():
            return
        if dialog.loeschen and t is not None:
            tm.eigenen_loeschen(t.id)
            self.z.meldung.emit("Termin gelöscht.", "ok")
        elif dialog.ergebnis is not None:
            neu = tm.eigenen_speichern(dialog.ergebnis)
            wann = f", Erinnerung ab {neu.datum - timedelta(days=neu.vorlauf):%d.%m.}" if neu.vorlauf >= 0 else ""
            self.z.meldung.emit(f"Termin am {neu.datum:%d.%m.%Y} gespeichert{wann}.", "ok")
        self.z.termine_geaendert.emit()

    def _autostart(self, an: bool) -> None:
        try:
            autostart.setzen(an)
            tm.einstellung_setzen(autostart=an)
            self.z.meldung.emit("Startet ab jetzt mit Windows im Infobereich." if an else "Autostart ausgeschaltet.", "ok")
        except OSError as exc:
            self.z.meldung.emit(f"Autostart nicht möglich: {exc}", "fehler")
            self.s_autostart.blockSignals(True)
            self.s_autostart.setChecked(autostart.aktiv())
            self.s_autostart.blockSignals(False)



class TagDialog(QDialog):
    """Alle Einträge eines Tages – mit Erledigt / Wieder offen / Öffnen und neuem Termin."""

    def __init__(self, seite: TermineSeite, d: date):
        super().__init__(seite)
        from ..dialoge import scrollbar_machen

        self.seite, self.d = seite, d
        self.setWindowTitle(_tag(d))
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        v.addWidget(label(_tag(d), "kartentitel"))
        self.liste = QVBoxLayout()
        self.liste.setSpacing(10)
        v.addLayout(self.liste)
        unten = QHBoxLayout()
        neu = knopf("Termin an diesem Tag", "ghost", "plus")
        neu.clicked.connect(lambda: self.seite._eigener(datum=self.d))
        unten.addWidget(neu)
        unten.addStretch()
        zu = knopf("Schließen", "primary")
        zu.clicked.connect(self.accept)
        unten.addWidget(zu)
        v.addLayout(unten)
        self.fuellen()
        scrollbar_machen(self, 760, 640)

    def fuellen(self) -> None:
        leeren(self.liste)
        ts = [t for t in self.seite.termine if t.datum == self.d]
        if not ts:
            self.liste.addWidget(label("Keine Termine an diesem Tag.", "muted"))
        offen = sum(1 for t in ts if t.erinnern_am is not None and not t.erledigt)
        if ts:
            self.liste.addWidget(label(f"{len(ts)} Einträge · {offen} Erinnerung(en) offen", "klein"))
        for t in ts:
            self.liste.addWidget(self.seite._zeile(t, mit_datum=False))
