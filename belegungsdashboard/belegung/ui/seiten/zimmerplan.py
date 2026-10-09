"""Zimmerplan Goslar: Zuteilen, Zeitstrahl, Häuser, Zimmer-Stammdaten und Quellen – je ein Reiter."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout,
    QLineEdit, QMenu, QMessageBox, QPushButton, QSizePolicy, QSpinBox, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ... import gebaeudeplan, speicher, uwt, zimmerexport
from ... import zimmerplan as zp
from .. import drucken, theme
from ..basis import Seite, Worker, Zustand
from ..widgets import FlowLayout, Hinweis, Karte, Leer, Mehrfachauswahl, Pille, Segment, Tabelle, DatumFeld, knopf, label, leeren
from ..zeitstrahl import Zeitstrahl

GESCHLECHTER = [("", "?"), ("m", "m"), ("w", "w"), ("d", "d")]
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]
HAEUSER = ["2", "3.1", "3.2", "3.3", "6"]
STATUS_TEXT = {"frei": "frei", "teilweise": "teilweise frei", "belegt": "belegt", "geplant": "geplant",
               "gesperrt": "gesperrt"}


def _status_farben() -> dict[str, tuple[str, str]]:
    t = theme.T
    return {"frei": (theme.alpha(t.ok, .20), t.text), "teilweise": (theme.alpha(t.knapp, .22), t.text),
            "belegt": (theme.alpha(t.text_3, .32), t.text),     # deutlich sichtbar, auch im dunklen Design
            "geplant": (theme.alpha(t.kategorie.get("Reha", t.accent), .22), t.text),   # blau wie im Zeitstrahl
            "gesperrt": (theme.alpha(t.ueber, .14), t.text_3)}


TABS = ["Zuteilen", "Aufgaben", "Zeitstrahl", "Häuser", "Reinigung", "Zimmer", "Quellen"]


def flur_text_lang(z: zp.Zimmer) -> str:
    return f"Zimmer {z.kurz} · {zp.flur_text(z)}"


class ZimmerplanSeite(Seite):
    titel = "Zimmerplan"
    untertitel = "Internat Goslar – Zimmer zuteilen und Belegung im Blick"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.stand: zp.Planstand | None = None
        self._zuteilungen: list[zp.Zuteilung] = []
        self._fest: dict[str, str] = {}
        self._anreise_kennung: str | None = None
        self._anreise_liste: list = []
        self._haus_filter: str | None = None
        self._monat = date.today().replace(day=1)
        zustand.listen_geaendert.connect(self.anstossen)   # auch ohne geladene Pivot aktualisieren

        # Reiter + kompakte Kennzahlen (statt großer Kacheln – passt auch bei 125/150 % Skalierung)
        kopf = QHBoxLayout()
        kopf.setSpacing(10)
        self.tabs = Segment(TABS, 0)
        self.tabs.geaendert.connect(self._tab)
        kopf.addWidget(self.tabs, 0, Qt.AlignTop)
        kopf.addStretch()
        self.lay.addLayout(kopf)
        # Kennzahlen in eigener Zeile unter den Reitern – brechen bei schmalem Fenster sauber um
        kz = QWidget()
        kz.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)   # nicht in die Höhe wachsen
        self.kennzahlen = FlowLayout(kz, abstand=6)
        self.lay.addWidget(kz)
        self.hinweise = QVBoxLayout()
        self.hinweise.setSpacing(8)
        self.lay.addLayout(self.hinweise)

        self._woche = date.today()
        self._zs_arten: set[str] = set()      # Zeitstrahl-Filter nach Art (Legende anklicken)
        self.seiten = [self._zuteilen_bauen(), self._aufgaben_bauen(), self._zeitstrahl_bauen(), self._haeuser_bauen(),
                       self._reinigung_bauen(), self._stamm_bauen(), self._quellen_bauen()]
        for w in self.seiten:
            self.lay.addWidget(w)
        self.lay.addStretch()
        self._tab_anzeigen(0)

    # ------------------------------------------------------------------ ohne Pivot-Daten lauffähig

    def anstossen(self) -> None:
        self._veraltet = True
        if self.isVisible():
            self._ausfuehren()

    def showEvent(self, e):
        QWidget.showEvent(self, e)
        if not self._veraltet and gebaeudeplan.neuer_plan_da():
            self._veraltet = True          # Word-Datei im Ordner „Gebaeudeplan“ wurde gespeichert
        if self._veraltet:
            self._ausfuehren()

    # ================================================================== Aufbau

    def _zuteilen_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        self.zu_karte = Karte(abstand=16)
        # Zeile 1: Anreise wählen
        wahl = QHBoxLayout()
        wahl.setSpacing(6)
        zurueck = knopf("", "icon", "links", "Vorherige Anreise")
        zurueck.clicked.connect(lambda: self._anreise_schritt(-1))
        vor = knopf("", "icon", "rechts", "Nächste Anreise")
        vor.clicked.connect(lambda: self._anreise_schritt(1))
        self.anreise = QComboBox()
        self.anreise.setMinimumContentsLength(28)
        self.anreise.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.anreise.currentIndexChanged.connect(self._anreise_combo)
        wahl.addWidget(zurueck)
        wahl.addWidget(self.anreise, 1)
        wahl.addWidget(vor)
        self.alle = QCheckBox("auch vergangene")
        self.alle.toggled.connect(lambda _a: self._anreisen_fuellen())
        wahl.addWidget(self.alle)
        self.zu_karte.inhalt.addLayout(wahl)
        # Zeile 2: Zusammenfassung (bricht bei wenig Platz um) und Aktionen
        unter = QHBoxLayout()
        unter.setSpacing(8)
        status = QWidget()
        self.zu_status = FlowLayout(status, abstand=6)
        unter.addWidget(status, 1)
        self.b_plus = knopf("Person", "ghost", "plus", "Person von Hand zu dieser Anreise hinzufügen")
        self.b_plus.clicked.connect(self._person_hinzufuegen)
        neu = knopf("Neu", "ghost", "funke", "Eigene Änderungen verwerfen und neu vorschlagen")
        neu.clicked.connect(self._neu_vorschlagen)
        self.b_excel = knopf("Export", "ghost", "tabelle", "Anreiseliste, Excel, Zimmerschilder oder Schlüsselliste dieser Anreise")
        export = QMenu(self.b_excel)
        export.addAction("Anreiseliste drucken …", lambda: self._anreise_drucken("anreise"))
        export.addAction("Excel-Liste (Zimmer, Etagen, freie Zimmer)", self._excel)
        export.addAction("Zimmerschilder drucken …", lambda: self._anreise_drucken("schilder"))
        export.addAction("Schlüsselliste drucken …", lambda: self._anreise_drucken("schluessel"))
        self.b_excel.setMenu(export)
        self.b_ok = knopf("Übernehmen", "primary", "haken", "Zuteilung speichern – zählt dann bei weiteren Vorschlägen als belegt")
        self.b_ok.clicked.connect(self._uebernehmen)
        self.b_zurueck = knopf("Zurücknehmen", "ghost", "loeschen", "Gespeicherte Planung wieder entfernen")
        menue = QMenu(self.b_zurueck)
        self.m_anreise = menue.addAction("Planung dieser Anreise zurücknehmen", self._anreise_zuruecknehmen)
        menue.addSeparator()
        self.m_uwt_weg = menue.addAction("Alle kommenden UWT-Planungen zurücknehmen", self._uwt_zuruecknehmen)
        menue.addAction("Alle kommenden UWT neu automatisch zuteilen", self._uwt_neu)
        menue.aboutToShow.connect(self._zurueck_menue)
        self.b_zurueck.setMenu(menue)
        aktionen = QWidget()            # Knöpfe brechen im schmalen Fenster um, statt die Seite zu verbreitern
        knoepfe = FlowLayout(aktionen, abstand=8)
        for x in (self.b_plus, neu, self.b_zurueck, self.b_excel, self.b_ok):
            knoepfe.addWidget(x)
        unter.addWidget(aktionen, 0, Qt.AlignTop)
        self.zu_karte.inhalt.addLayout(unter)
        # Name und Maßnahme zweizeilig in einer Spalte – so bleibt der Name auch im schmalen Fenster lesbar
        self.zu_tabelle = Tabelle(["Name", "m/w", "Tier", "Zeitraum", "Zimmer", ""],
                                  ["l", "l", "l", "l", "l", "l"], dehnen=0)
        self.zu_tabelle.setWordWrap(True)
        self.zu_tabelle.setSelectionMode(QAbstractItemView.NoSelection)
        self.zu_karte.inhalt.addWidget(self.zu_tabelle)
        self.zu_hinweise = label("", "klein", umbruch=True)
        self.zu_karte.inhalt.addWidget(self.zu_hinweise)
        self.zu_leer = Leer("personen", "Keine Anreisen", "Anreiselisten oder den UWT-Plan unter Daten & Import "
                                                          "hochladen – oder eine Person von Hand anlegen.", "Person hinzufügen")
        self.zu_leer.knopf.clicked.connect(self._person_hinzufuegen)
        self.zu_karte.inhalt.addWidget(self.zu_leer)
        v.addWidget(self.zu_karte)
        return w

    def _zeitstrahl_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        leiste = QHBoxLayout()
        leiste.setSpacing(8)
        zurueck = knopf("", "icon", "links", "Vorheriger Monat")
        zurueck.clicked.connect(lambda: self._monat_wechseln(-1))
        vor = knopf("", "icon", "rechts", "Nächster Monat")
        vor.clicked.connect(lambda: self._monat_wechseln(1))
        heute = knopf("Heute", "ghost")
        heute.clicked.connect(lambda: self._monat_wechseln(0))
        self.monat_text = label("", "kartentitel")
        self.monat_text.setMinimumWidth(150)
        for x in (zurueck, self.monat_text, vor, heute):
            leiste.addWidget(x)
        leiste.addStretch()
        self.zs_anzahl = label("", "klein")
        self.zs_anzahl.setToolTip("Zimmer oder Balken anklicken für Details")
        leiste.addWidget(self.zs_anzahl)
        v.addLayout(leiste)
        # Häuser in eigener Zeile – sonst wird es bei schmalem Fenster rechts abgeschnitten
        haus_zeile = QHBoxLayout()
        self.zs_haus = Segment(["Haus 2", "Haus 3.1", "Haus 3.2", "Haus 3.3", "Haus 6", "Alle"], 0)
        self.zs_haus.geaendert.connect(lambda _i: self._zeitstrahl_zeigen())
        haus_zeile.addWidget(self.zs_haus)
        haus_zeile.addStretch()
        v.addLayout(haus_zeile)
        leiste = QHBoxLayout()
        self.zs_suche = QLineEdit()
        self.zs_suche.setPlaceholderText("Name oder Zimmer suchen …")
        self.zs_suche.setClearButtonEnabled(True)
        self.zs_suche.setFixedWidth(200)
        self.zs_suche.textChanged.connect(lambda _t: self._zeitstrahl_zeigen())
        leiste.addWidget(self.zs_suche)
        leiste.addSpacing(12)
        leiste.addWidget(label("Gruppe", "klein"))
        self.zs_gruppe = Mehrfachauswahl([(g, zp.GRUPPE_LABEL.get(g, g)) for g in zp.GRUPPEN], "Alle Gruppen")
        self.zs_gruppe.geaendert.connect(lambda _g: self._zeitstrahl_zeigen())
        leiste.addWidget(self.zs_gruppe)
        self.zs_modus = QComboBox()
        self.zs_modus.addItem("wohnt dort", "wohnt")
        self.zs_modus.addItem("darf dort wohnen", "darf")
        self.zs_modus.setToolTip("„wohnt dort“: Zimmer, in denen die Gruppe im Monat wohnt – andere Belegungen blass\n"
                                 "„darf dort wohnen“: laut Regeln für die Gruppe erlaubte Zimmer")
        self.zs_modus.currentIndexChanged.connect(lambda _i: self._zeitstrahl_zeigen())
        leiste.addWidget(self.zs_modus)
        leiste.addStretch()
        v.addLayout(leiste)
        leg = QWidget()
        leg.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.zs_legende = FlowLayout(leg, abstand=14)
        v.addWidget(leg)
        karte = Karte(abstand=8)
        self.zeitstrahl = Zeitstrahl()
        self.zeitstrahl.zimmer_geklickt.connect(self._zimmer_details)
        self.zeitstrahl.verschiebbar = True           # geplante Balken in ein anderes Zimmer ziehen
        self.zeitstrahl.verschieben.connect(self._zs_verschieben)
        karte.inhalt.addWidget(self.zeitstrahl)
        v.addWidget(karte)
        return w

    def _reinigung_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        leiste = QHBoxLayout()
        leiste.setSpacing(8)
        zurueck = knopf("", "icon", "links", "Vorherige Woche")
        zurueck.clicked.connect(lambda: self._woche_wechseln(-1))
        vor = knopf("", "icon", "rechts", "Nächste Woche")
        vor.clicked.connect(lambda: self._woche_wechseln(1))
        heute = knopf("Diese Woche", "ghost")
        heute.clicked.connect(lambda: self._woche_wechseln(0))
        self.rg_titel = label("", "kartentitel")
        for x in (zurueck, self.rg_titel, vor, heute):
            leiste.addWidget(x)
        leiste.addStretch()
        # Ausgabe-Knöpfe oben neben der Woche – die Optionen darunter in eigener Zeile (passt auch schmal)
        for text, icon, fn in (("Drucken", "datei", self._reinigung_drucken), ("PDF", "datei", self._reinigung_pdf),
                               ("Excel", "tabelle", self._reinigung_excel)):
            b = knopf(text, "primary" if text == "Drucken" else "ghost", icon)
            b.clicked.connect(fn)
            leiste.addWidget(b)
        v.addLayout(leiste)
        leiste = QHBoxLayout()
        leiste.setSpacing(16)
        self.rg_anreisetag = QCheckBox("Vorbereiten am Anreisetag")
        self.rg_anreisetag.setToolTip("Nur für leer stehende Zimmer: Aus (Standard) = am letzten Werktag vor der "
                                      "Anreise (Sonntag/Montag-Anreisen also am Freitag). An = am Anreisetag selbst.")
        self.rg_anreisetag.setChecked(bool(speicher.einstellungen().get("reinigung_anreisetag", False)))
        self.rg_anreisetag.toggled.connect(lambda an: (speicher.einstellung_setzen("reinigung_anreisetag", an),
                                                       self._reinigung_zeigen()))
        leiste.addWidget(self.rg_anreisetag)
        self.rg_ausblenden = QCheckBox("Erledigte ausblenden")
        self.rg_ausblenden.setChecked(bool(speicher.einstellungen().get("reinigung_ausblenden", False)))
        self.rg_ausblenden.toggled.connect(lambda an: (speicher.einstellung_setzen("reinigung_ausblenden", an),
                                                       self._reinigung_zeigen()))
        leiste.addWidget(self.rg_ausblenden)
        leiste.addStretch()
        v.addLayout(leiste)
        self.rg_info = label("", "klein", umbruch=True)
        v.addWidget(self.rg_info)
        # „Jetzt wichtig“: offene Reinigungen nach Priorität – auch überfällige aus den Vorwochen
        self.rg_wichtig = QVBoxLayout()
        self.rg_wichtig.setSpacing(10)
        v.addLayout(self.rg_wichtig)
        self.rg_tage = QVBoxLayout()
        self.rg_tage.setSpacing(16)
        v.addLayout(self.rg_tage)
        return w

    def _haeuser_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        leiste = QHBoxLayout()
        leiste.setSpacing(8)
        leiste.addWidget(label("Stand am", "klein"))
        self.tag = DatumFeld(date.today())
        self.tag.geaendert.connect(lambda _d: self._haeuser_zeigen())
        leiste.addWidget(self.tag)
        leiste.addSpacing(16)
        chips = QWidget()
        chips.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        chip_lay = FlowLayout(chips, abstand=8)      # Status-Chips brechen bei wenig Platz um
        self.filter_gruppe = QButtonGroup(self)
        self.filter_gruppe.setExclusive(True)
        self.filter_knoepfe: dict[str | None, QPushButton] = {}
        for schluessel, text in ((None, "Alle"), ("frei", "Frei"), ("teilweise", "Teilweise frei"), ("belegt", "Belegt"),
                                 ("geplant", "Geplant"), ("gesperrt", "Gesperrt")):
            b = knopf(text, "chip")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, s=schluessel: self._filter_setzen(s))
            self.filter_gruppe.addButton(b)
            self.filter_knoepfe[schluessel] = b
            chip_lay.addWidget(b)
        self.filter_knoepfe[None].setChecked(True)
        # Personengruppen: wer wohnt dort – oder wo darf die Gruppe laut Regeln wohnen
        zweite = leiste
        zweite.addWidget(label("Gruppe", "klein"))
        self.h_gruppe = Mehrfachauswahl([(g, zp.GRUPPE_LABEL.get(g, g)) for g in zp.GRUPPEN], "Alle Gruppen")
        self.h_gruppe.geaendert.connect(lambda _g: self._haeuser_zeigen())
        zweite.addWidget(self.h_gruppe)
        self.h_modus = QComboBox()
        self.h_modus.addItem("wohnt dort", "wohnt")
        self.h_modus.addItem("darf dort wohnen", "darf")
        self.h_modus.setToolTip("„wohnt dort“: am gewählten Tag belegt bzw. geplant von dieser Gruppe\n"
                                "„darf dort wohnen“: laut Regeln erlaubt – mit „Frei“ kombiniert: wo ist Platz für die Gruppe")
        self.h_modus.currentIndexChanged.connect(lambda _i: self._haeuser_zeigen())
        zweite.addWidget(self.h_modus)
        zweite.addStretch()
        v.addLayout(leiste)
        v.addWidget(chips)
        export = knopf("Freie Zimmer als Excel", "ghost", "tabelle")
        export.clicked.connect(self._excel_frei)
        chip_lay.addWidget(export)
        leg = QWidget()
        leg.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.h_legende = FlowLayout(leg, abstand=10)
        v.addWidget(leg)
        v.addWidget(label("Zimmer anklicken für Details · D = Doppel · T = Tiere · M = nur Männer · G = Gäste", "klein"))
        self.haeuser = QVBoxLayout()
        self.haeuser.setSpacing(16)
        v.addLayout(self.haeuser)
        return w

    def _stamm_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        karte = Karte("Zimmer-Stammdaten", "Aus den Grundrissen abgeleitet – bitte einmal prüfen. Häkchen per Klick, "
                                           "Flur/Betten/Notiz per Doppelklick ändern, dann speichern.")
        leiste = QHBoxLayout()
        self.stamm_haus = Segment(["Haus 2", "Haus 3.1", "Haus 3.2", "Haus 3.3", "Haus 6"], 0)
        self.stamm_haus.geaendert.connect(lambda _i: self._stamm_zeigen())
        leiste.addWidget(self.stamm_haus)
        leiste.addStretch()
        speichern = knopf("Speichern", "primary", "haken")
        speichern.clicked.connect(self._stamm_speichern)
        leiste.addWidget(speichern)
        karte.inhalt.addLayout(leiste)
        self.stamm = Tabelle(["Zimmer", "Etage", "Flur", "Betten", "Nur Männer", "Tiere", "Gäste", "Im Internat", "Notiz"],
                             ["l", "l", "l", "r", "l", "l", "l", "l", "l"], dehnen=8)
        self.stamm.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.stamm.setFocusPolicy(Qt.StrongFocus)
        karte.inhalt.addWidget(self.stamm)
        v.addWidget(karte)
        return w

    def _aufgaben_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        k = Karte("Im Belegungssystem eintragen",
                  "Hier geplant, aber noch nicht im Gebäudeplan. Nach dem Eintragen abhaken – steht die Person im "
                  "nächsten Gebäudeplan, verschwindet sie von selbst. Wird das Zimmer geändert, ist der Haken wieder weg.")
        zeile = QHBoxLayout()
        zeile.setSpacing(12)
        self.ei_zeitraum = Segment(["Nächste 2 Wochen", "8 Wochen", "Alle"], 0)
        self.ei_zeitraum.geaendert.connect(lambda _i: self._eintragen_zeigen())
        zeile.addWidget(self.ei_zeitraum)
        self.ei_fertig = QCheckBox("Abgehakte ausblenden")
        self.ei_fertig.setChecked(True)
        self.ei_fertig.toggled.connect(lambda _a: self._eintragen_zeigen())
        zeile.addWidget(self.ei_fertig)
        zeile.addStretch()
        k.inhalt.addLayout(zeile)
        self.ei_info = label("", "klein", umbruch=True)
        k.inhalt.addWidget(self.ei_info)
        self.ei_inhalt = QVBoxLayout()
        self.ei_inhalt.setSpacing(14)
        k.inhalt.addLayout(self.ei_inhalt)
        v.addWidget(k)

        self.fc_karte = Karte("Facility-Check nach langem Aufenthalt",
                              "Nach einem Auszug nach langer Maßnahme: Elektrik prüfen, Fensterwartung. Erledigtes abhaken. "
                              "Ab wie vielen Monaten: Quellen → Planung.")
        self.fc_inhalt = QVBoxLayout()
        self.fc_karte.inhalt.addLayout(self.fc_inhalt)
        v.addWidget(self.fc_karte)

        wb = Karte("Wochenblatt", "An- und Abreisen und Reinigungen je Tag – zum Aushängen für Hausmeister und Reinigung")
        zeile = QHBoxLayout()
        zeile.setSpacing(10)
        self.wb_woche = QComboBox()
        heute = date.today()
        for i in range(4):
            montag = heute - timedelta(days=heute.weekday()) + timedelta(weeks=i)
            text = ["Diese Woche", "Nächste Woche", "In 2 Wochen", "In 3 Wochen"][i]
            self.wb_woche.addItem(f"{text} · KW {montag.isocalendar()[1]} ({montag:%d.%m.}–{montag + timedelta(days=6):%d.%m.})",
                                  montag)
        zeile.addWidget(self.wb_woche)
        self.wb_namen = QCheckBox("mit Namen")
        self.wb_namen.setChecked(True)
        zeile.addWidget(self.wb_namen)
        drucken = knopf("Drucken", "ghost", "datei")
        drucken.clicked.connect(lambda: self._wochenblatt(False))
        pdf = knopf("PDF", "ghost", "runter")
        pdf.clicked.connect(lambda: self._wochenblatt(True))
        zeile.addWidget(drucken)
        zeile.addWidget(pdf)
        zeile.addStretch()
        wb.inhalt.addLayout(zeile)
        v.addWidget(wb)

        ek = Karte("Engpässe – nächste 12 Wochen",
                   "Zimmer, die die ganze Woche frei sind, nach heutigem Stand. Anreisen ohne Liste fehlen noch – "
                   "in Wirklichkeit wird es eher enger.")
        self.eng_tab = Tabelle(["KW", "Woche", "Freie Zimmer", "EMR-Zimmer", "Doppelzimmer UWT", "Lage"],
                               ["l", "l", "r", "r", "r", "l"], dehnen=5)
        self.eng_tab.setToolTip("EMR-Zimmer: Haus 2, 1.–2. OG · Doppelzimmer UWT: ganz frei in Haus 3.2, 3.3 und 6")
        ek.inhalt.addWidget(self.eng_tab)
        v.addWidget(ek)
        v.addStretch()
        return w

    def _quellen_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        # Karten untereinander: so umbrechen die Texte sauber und nichts wird abgeschnitten
        zeile = QVBoxLayout()
        zeile.setSpacing(16)
        self.plan_karte = Karte("Gebäudeplan", "Word-Export aus dem Belegungssystem – Grundlage für Zimmer und Belegung")
        self.plan_text = label("", "muted", umbruch=True)
        self.plan_karte.inhalt.addWidget(self.plan_text)
        knoepfe = QHBoxLayout()
        knoepfe.setSpacing(8)
        imp = knopf("Gebäudeplan importieren", "primary", "hochladen")
        imp.clicked.connect(self._plan_importieren)
        knoepfe.addWidget(imp)
        einf = knopf("Aus Zwischenablage einfügen", "ghost", "kopieren")
        einf.setToolTip("Im Belegungssystem die Gebäudeansicht markieren (Strg+A) und kopieren (Strg+C) – dann hier klicken")
        einf.clicked.connect(self._plan_einfuegen)
        knoepfe.addWidget(einf)
        ordner = knopf("Ordner öffnen", "ghost", "datei")
        ordner.setToolTip("Gebäudepläne (.docx), die hier liegen, werden beim Öffnen des Zimmerplans automatisch übernommen")
        ordner.clicked.connect(self._eingang_oeffnen)
        knoepfe.addWidget(ordner)
        knoepfe.addStretch()
        self.plan_karte.inhalt.addLayout(knoepfe)
        zeile.addWidget(self.plan_karte, 1)
        self.pivot_karte = Karte("Zimmer-Pivot", "Belegung je Zimmer und Tag (Rios) – ergänzt Buchungen, die im Plan fehlen")
        self.pivot_text = label("", "muted", umbruch=True)
        self.pivot_karte.inhalt.addWidget(self.pivot_text)
        self.b_pivot = knopf("Zimmer-Pivot importieren", "primary", "tabelle")
        self.b_pivot.clicked.connect(self._pivot_importieren)
        self.pivot_karte.inhalt.addWidget(self.b_pivot, 0, Qt.AlignLeft)
        zeile.addWidget(self.pivot_karte, 1)
        v.addLayout(zeile)
        einst = Karte("Planung", "Gilt für alle Vorschläge")
        f = QHBoxLayout()
        f.addWidget(label("Puffer nach jeder Abreise (Reinigung)", "klein"))
        self.puffer = QSpinBox()
        self.puffer.setRange(0, 7)
        self.puffer.setSuffix(" Tag(e)")
        self.puffer.setToolTip("0 = am Abreisetag wieder belegbar · 1 = frühestens am Tag nach der Abreise")
        self.puffer.setValue(int(speicher.einstellungen().get("zimmer_puffer", 1)))
        self.puffer.valueChanged.connect(lambda v: (speicher.einstellung_setzen("zimmer_puffer", v), self.neu_laden()))
        f.addWidget(self.puffer)
        f.addStretch()
        einst.inhalt.addLayout(f)
        f = QHBoxLayout()                  # eigene Zeile – passt auch im schmalen Fenster
        f.addWidget(label("Facility-Check ab Aufenthalt von", "klein"))
        self.fc_monate = QSpinBox()
        self.fc_monate.setRange(1, 36)
        self.fc_monate.setSuffix(" Monaten")
        self.fc_monate.setToolTip("Nach einem Auszug nach so langer Zeit: Meldung „Elektrik prüfen, Fensterwartung“")
        self.fc_monate.setValue(int(speicher.einstellungen().get("facility_monate", 6)))
        self.fc_monate.valueChanged.connect(lambda v: (speicher.einstellung_setzen("facility_monate", v),
                                                       self._tab_inhalt(self.tabs.index())))
        f.addWidget(self.fc_monate)
        f.addStretch()
        einst.inhalt.addLayout(f)
        v.addWidget(einst)
        self.prot_karte = Karte("Änderungsprotokoll", "Wer wann wen in welches Zimmer geplant, umgeplant oder entfernt hat "
                                                      "(neueste zuerst)")
        self.prot_tab = Tabelle(["Zeit", "Aktion", "Name", "Zimmer", "Anlass", "Wer"], ["l"] * 6, dehnen=2)
        self.prot_tab.setTextElideMode(Qt.ElideRight)
        self.prot_karte.inhalt.addWidget(self.prot_tab)
        self.prot_mehr = knopf("Ältere anzeigen", "ghost")
        self.prot_mehr.clicked.connect(lambda: self._protokoll_zeigen(self._prot_anzahl + 100))
        self.prot_karte.inhalt.addWidget(self.prot_mehr, 0, Qt.AlignLeft)
        self._prot_anzahl = 30
        v.addWidget(self.prot_karte)
        v.addStretch()
        return w

    # ================================================================== Anzeige

    def aktualisieren(self) -> None:
        self.neu_laden()

    def neu_laden(self) -> None:
        neu = gebaeudeplan.automatisch_importieren()
        if neu is not None:
            belegt = sum(1 for b in neu.belegungen if b.art == "belegt")
            stand = f" (Stand {neu.stand:%d.%m.%Y})" if neu.stand else ""
            self.z.meldung.emit(f"Gebäudeplan {neu.datei}{stand} automatisch übernommen: {belegt} Belegungen.", "ok")
        uwt_neu = uwt.automatisch_importieren()
        if uwt_neu:
            from ..hauptfenster import uwt_meldung

            self.z.meldung.emit(uwt_meldung(uwt_neu), "ok")
        self.stand = zp.laden()
        if neu is not None and (k := zp.konflikte(self.stand.lage)):
            self.z.meldung.emit(f"Achtung: {len(k)} geplante Zimmer kollidieren mit dem neuen Gebäudeplan – "
                                "Hinweis im Zimmerplan, „Neu planen“ löst es.", "warnung")
        # kommende UWT gleich zuteilen (DZ-Partner zusammen) – jede Person nur einmal automatisch
        try:
            auto = zp.uwt_automatisch_zuteilen(self.stand)
        except Exception:
            auto = []
        if auto:
            self.stand = zp.laden()
            klassen = sorted({zt.bedarf.massnahme.removeprefix("UWT ") for zt in auto})
            self.z.meldung.emit(f"UWT automatisch zugeteilt: {len(auto)} Personen ({', '.join(klassen)}) – "
                                "unter Zuteilen änderbar.", "ok")
        self._kopf_zeigen()
        self._aufgaben_zaehler()
        self._quellen_zeigen()
        ziel = getattr(self.z, "zimmer_anreise", None)
        if ziel:
            # EMR sind schon am Vortag des Listendatums da – dann den Vortag wählen
            self._anreise_kennung = self._kennung_fuer_liste(ziel)
            self.z.zimmer_anreise = None
            self.tabs.setzen(0)
            self._tab_anzeigen(0)
        self._anreisen_fuellen()
        self._tab_inhalt(self.tabs.index())

    def _tab(self, i: int) -> None:
        self._tab_anzeigen(i)
        self._tab_inhalt(i)

    def _tab_anzeigen(self, i: int) -> None:
        for k, w in enumerate(self.seiten):
            w.setVisible(k == i)

    def _tab_inhalt(self, i: int) -> None:
        if self.stand is None or not 0 <= i < len(TABS):
            return
        {"Aufgaben": self._aufgaben_zeigen, "Zeitstrahl": self._zeitstrahl_zeigen, "Häuser": self._haeuser_zeigen,
         "Reinigung": self._reinigung_zeigen, "Zimmer": self._stamm_zeigen}.get(TABS[i], lambda: None)()

    def _kopf_zeigen(self) -> None:
        st = self.stand
        heute = date.today()
        zaehler = {"frei": 0, "belegt": 0, "gesperrt": 0}
        for z in st.zimmer:
            if not z.aktiv:
                continue
            status, _ = st.lage.status_am(z.id, heute)
            if status == "teilweise":
                zaehler["frei"] += 1
                zaehler["belegt"] += 1
            elif status == "geplant":
                zaehler["belegt"] += 1
            else:
                zaehler[status] = zaehler.get(status, 0) + 1
        offen = sum(1 for b in st.bedarf if heute <= b.von <= heute + timedelta(weeks=8) and not st.zugewiesen(b.schluessel))
        leeren(self.kennzahlen)
        for text, stufe, tip in ((f"{zaehler['frei']} frei", "ok", "Freie Zimmer heute (inkl. teilweise freier Doppelzimmer)"),
                                 (f"{zaehler['belegt']} belegt", "neutral", "Belegte Zimmer heute"),
                                 (f"{zaehler['gesperrt']} gesperrt", "neutral", "Gesperrt oder in Renovierung"),
                                 (f"{offen} ohne Zimmer", "knapp" if offen else "ok", "Anreisen der nächsten 8 Wochen ohne übernommenes Zimmer")):
            p = Pille(text, stufe)
            p.setToolTip(tip)
            self.kennzahlen.addWidget(p)
        leeren(self.hinweise)
        if st.plan is None:
            h = Hinweis("Noch kein Gebäudeplan da – die Zimmer sind bekannt, die aktuelle Belegung aber nicht. "
                        "Plan importieren oder in den Ordner „Gebaeudeplan“ legen.",
                        "warnung", "Gebäudeplan importieren")
            h.knopf.clicked.connect(self._plan_importieren)
            self.hinweise.addWidget(h)
        elif st.plan.stand and (heute - st.plan.stand).days > 7:
            h = Hinweis(f"Der Gebäudeplan ist vom {st.plan.stand:%d.%m.%Y} – für verlässliche Vorschläge bitte den "
                        "aktuellen Plan importieren.", "info", "Importieren")
            h.knopf.clicked.connect(self._plan_importieren)
            self.hinweise.addWidget(h)
        fremd = sorted((b for zid, bs in st.lage.belegungen.items() if zp.nur_emr(st.lage.zimmer[zid]) for b in bs
                        if b.bis >= heute and zp.belegung_gruppe(b) not in (None, "EMR")), key=lambda b: b.zimmer)
        if fremd:
            self.hinweise.addWidget(Hinweis(
                "<b>Haus 2, Zimmer 101–110 sind nur für EMR</b> – laut Gebäudeplan wohnen dort noch andere: "
                + ", ".join(f"{b.name} ({b.zimmer.removeprefix('GS-')}, bis {b.bis:%d.%m.})" for b in fremd)
                + ". Neue Vorschläge kommen dort nicht mehr hin.", "info"))
        self._konflikte = zp.konflikte(st.lage, heute)
        if self._konflikte:
            k = self._konflikte
            zeilen = [x.text for x in k[:6]] + ([f"… und {len(k) - 6} weitere"] if len(k) > 6 else [])
            h = Hinweis(f"<b>Konflikt mit dem Gebäudeplan – {len(k)} geplante "
                        f"{'Zimmer ist' if len(k) == 1 else 'Zimmer sind'} inzwischen belegt oder gesperrt:</b><br>"
                        + "<br>".join(zeilen), "fehler", "Neu planen")
            h.setToolTip("<br>".join(x.text for x in k))
            h.knopf.setToolTip("Für diese Personen (und ihre DZ-Partner) ein freies Zimmer suchen und speichern")
            h.knopf.clicked.connect(self._konflikte_loesen)
            self.hinweise.addWidget(h)
        dz_hinweise = [h for h in (uwt.klassen_info().get("hinweise") or []) if "noch keine DZ-Liste" not in h]
        if dz_hinweise:
            self.hinweise.addWidget(Hinweis("<b>UWT-Klassenübersicht:</b> " + " ".join(dz_hinweise), "info"))
        anders = [a for a in st.lage.abgleich if a.art == "anders"]
        fehlt = [a for a in st.lage.abgleich if a.art == "fehlt"]
        for liste, titel, art in ((anders, "Im Gebäudeplan anders gebucht als geplant", "info"),
                                  (fehlt, "Angereist? Im Gebäudeplan noch nicht gebucht", "warnung")):
            if not liste:
                continue
            zeilen = [a.text for a in liste[:6]] + ([f"… und {len(liste) - 6} weitere"] if len(liste) > 6 else [])
            h = Hinweis(f"<b>{titel} ({len(liste)}):</b><br>" + "<br>".join(zeilen), art)
            h.setToolTip("<br>".join(a.text for a in liste))
            self.hinweise.addWidget(h)

    # ================================================================== Zuteilen

    def _anreisen_fuellen(self) -> None:
        if self.stand is None:
            return
        ab = date(2000, 1, 1) if self.alle.isChecked() else date.today() - timedelta(days=3)
        self._anreise_liste = self.stand.anreisen(ab)
        kennungen = [k for k, *_ in self._anreise_liste]
        if self._anreise_kennung not in kennungen:
            # ohne Auswahl: nächste Anreise, die noch nicht vollständig zugeteilt ist
            offen = [k for k, _t, _x, bs in self._anreise_liste if not all(self.stand.zugewiesen(b.schluessel) for b in bs)]
            self._anreise_kennung = (offen or kennungen or [None])[0]
        self.anreise.blockSignals(True)
        self.anreise.clear()
        for kennung, tag, titel, bs in self._anreise_liste:
            fertig = sum(1 for b in bs if self.stand.zugewiesen(b.schluessel))
            stand = "✓ zugeteilt" if fertig == len(bs) else (f"{fertig}/{len(bs)} zugeteilt" if fertig else "offen")
            self.anreise.addItem(f"{WOCHENTAGE[tag.weekday()]} {tag:%d.%m.%Y}  ·  {titel}  ·  {len(bs)} Pers.  ·  {stand}", kennung)
            self.anreise.setItemData(self.anreise.count() - 1, titel, Qt.ToolTipRole)
        if self._anreise_kennung in kennungen:
            self.anreise.setCurrentIndex(kennungen.index(self._anreise_kennung))
        self.anreise.blockSignals(False)
        self.anreise.setEnabled(bool(kennungen))
        self._anreise_gewaehlt()

    def _anreise_combo(self, i: int) -> None:
        if 0 <= i < len(self._anreise_liste):
            self._anreise_kennung = self._anreise_liste[i][0]
            self._anreise_gewaehlt()

    def _anreise_schritt(self, schritt: int) -> None:
        i = self.anreise.currentIndex() + schritt
        if 0 <= i < self.anreise.count():
            self.anreise.setCurrentIndex(i)

    def _bedarf(self) -> list[zp.Bedarf]:
        if not self._anreise_kennung or self.stand is None:
            return []
        return sorted((b for b in self.stand.bedarf if b.von.isoformat() == self._anreise_kennung),
                      key=lambda b: (b.anreise_kennung, b.name))

    def _anreise_gewaehlt(self) -> None:
        bedarf = self._bedarf()
        self._fest = {b.schluessel: z["zimmer"] for b in bedarf if (z := self.stand.zugewiesen(b.schluessel))}
        self._berechnen()

    def _neu_vorschlagen(self) -> None:
        self._fest = {}
        self._berechnen()

    def _berechnen(self) -> None:
        bedarf = self._bedarf()
        self.zu_leer.setVisible(not bedarf)
        self.zu_tabelle.setVisible(bool(bedarf))
        for b in (self.b_ok, self.b_excel):
            b.setEnabled(bool(bedarf))
        self.b_plus.setEnabled(True)
        if not bedarf:
            self._zuteilungen = []
            leeren(self.zu_status)
            self.zu_hinweise.setText("")
            return
        self._zuteilungen = zp.vorschlagen(self.stand.lage, bedarf, self._fest)
        self._tabelle_fuellen()

    def _tabelle_fuellen(self) -> None:
        t = theme.T
        zeilen, farben, hinweise = [], {}, []
        abgleich: dict[str, list[str]] = {}
        for a in self.stand.lage.abgleich:
            abgleich.setdefault(a.person, []).append(a.text.split(": ", 1)[1])
        for r, zt in enumerate(self._zuteilungen):
            b = zt.bedarf
            g = QComboBox()
            for wert, text in GESCHLECHTER:
                g.addItem(text + ("*" if wert and wert == b.geschlecht and b.geschlecht_geschaetzt else ""), wert)
            g.setCurrentIndex(max(0, g.findData(b.geschlecht)))
            g.setMinimumWidth(70)
            if b.geschlecht_geschaetzt and b.geschlecht:
                g.setToolTip("* aus dem Vornamen geschätzt – bitte prüfen")
            g.currentIndexChanged.connect(lambda _i, b=b, g=g: self._angabe(b, geschlecht=g.currentData()))
            tier = QCheckBox()
            tier.setChecked(b.tier)
            tier.toggled.connect(lambda an, b=b: self._angabe(b, tier=an))
            zim = QComboBox()
            zim.addItem("— nicht zugeteilt —", None)
            for z in zt.alternativen:
                # Etage steckt in der Nummer (219 = 2. OG) – kurz halten, damit der Name Platz hat
                zim.addItem(z.kurz + (" · DZ" if z.betten > 1 else ""), z.id)
                zim.setItemData(zim.count() - 1, f"{flur_text_lang(z)}" + (" · Doppelzimmer" if z.betten > 1 else ""),
                                Qt.ToolTipRole)
            if zt.ausnahmen:              # weitere freie Zimmer nur von Hand (Ausnahme) – unten, abgesetzt
                zim.insertSeparator(zim.count())
                for z in zt.ausnahmen:
                    grund = zp.ausnahme_grund(self.stand.lage, z, b)
                    zim.addItem(f"{z.kurz} · {grund}" + (" · DZ" if z.betten > 1 else ""), z.id)
                    zim.setItemData(zim.count() - 1, f"Ausnahme ({grund}) – wird nie automatisch vorgeschlagen, "
                                    "von Hand möglich", Qt.ToolTipRole)
            if zt.zimmer:
                zim.setCurrentIndex(max(0, zim.findData(zt.zimmer.id)))
            zim.currentIndexChanged.connect(lambda _i, b=b, zim=zim: self._zimmer(b, zim.currentData()))
            # so breit wie das gewählte Zimmer – die aufgeklappte Liste zeigt alle Texte voll
            fm = zim.fontMetrics()
            zim.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            zim.setMinimumContentsLength(1)
            zim.setMinimumWidth(max(fm.horizontalAdvance(zim.currentText()) + 56, 140))
            zim.view().setMinimumWidth(max(fm.horizontalAdvance(zim.itemText(i)) for i in range(zim.count())) + 48)
            probleme = ([zt.grund] if zt.zimmer is None else []) + zt.warnungen + abgleich.get(b.schluessel, [])
            zeit = f"{b.von:%d.%m.}–{'≈' if b.bis_angenommen else ''}{b.bis:%d.%m.%y}"
            zweite = b.massnahme.removeprefix("UWT ") if b.gruppe == "UWT" else b.massnahme
            if b.dz == "allein":
                zweite += " · allein"
            elif b.dz:
                partner = [x.bedarf.name.split(",")[0] for x in self._zuteilungen if x.bedarf.dz == b.dz and x.bedarf is not b]
                zweite += f" · DZ: {', '.join(partner)}" if partner else ""
            zeilen.append([f"{b.name}\n{zweite}" if zweite else b.name, self._zelle(g), self._zelle(tier, 12),
                           zeit, self._zelle(zim), "⚠" if probleme else "✓"])
            farben[(r, 5)] = t.ueber if zt.zimmer is None else (t.knapp if probleme else t.ok)
            if probleme:
                hinweise.append(f"<b>{b.name}</b>: " + "; ".join(probleme))
        self.zu_tabelle.fuellen(zeilen, farben)
        for r, zt in enumerate(self._zuteilungen):
            probleme = ([zt.grund] if zt.zimmer is None else []) + zt.warnungen + abgleich.get(zt.bedarf.schluessel, [])
            for c in (0, 5):
                if self.zu_tabelle.item(r, c):
                    tip = "<br>".join(probleme) if probleme else zt.grund
                    dz = ("<br>laut DZ-Liste allein" if zt.bedarf.dz == "allein" else
                          "<br>DZ-Partner: " + ", ".join(x.bedarf.name for x in self._zuteilungen
                                                          if x.bedarf.dz == zt.bedarf.dz and x is not zt) if zt.bedarf.dz else "")
                    self.zu_tabelle.item(r, c).setToolTip(f"<b>{zt.bedarf.name}</b> · {zt.bedarf.massnahme}{dz}<br>{tip}"
                                                          if c == 0 else tip)
        self.zu_hinweise.setText("<br>".join(hinweise))
        self.zu_hinweise.setVisible(bool(hinweise))
        self.zu_tabelle.widgets_einpassen()
        vh = self.zu_tabelle.verticalHeader()     # Platz für Name + Maßnahme (zwei Zeilen)
        vh.setDefaultSectionSize(max(vh.defaultSectionSize(), self.zu_tabelle.fontMetrics().lineSpacing() * 2 + 26))
        self.zu_tabelle.hoehe_anpassen(18)
        self._status_zeigen()

    @staticmethod
    def _zelle(w: QWidget, links: int = 4) -> QWidget:
        h = QWidget()
        lay = QHBoxLayout(h)
        lay.setContentsMargins(links, 0, 4, 0)
        lay.addWidget(w, 0, Qt.AlignVCenter)
        lay.addStretch()
        return h

    def _status_zeigen(self) -> None:
        leeren(self.zu_status)
        zts = self._zuteilungen
        ok = [z for z in zts if z.zimmer]
        self.zu_status.addWidget(Pille(f"{len(ok)} von {len(zts)} untergebracht", "ok" if len(ok) == len(zts) else "knapp"))
        if zts:
            tag = zts[0].bedarf.von
            frei = sum(1 for z in self.stand.zimmer if z.aktiv and not z.gaeste
                       and self.stand.lage.status_am(z.id, tag)[0] in ("frei", "teilweise"))
            p = Pille(f"{frei} Zimmer frei", "neutral")
            p.setToolTip(f"Freie Zimmer im Internat (ohne Gästezimmer) am {tag:%d.%m.%Y}, vor dieser Zuteilung.")
            self.zu_status.addWidget(p)
        warn = sum(1 for z in zts if z.warnungen)
        if warn:
            self.zu_status.addWidget(Pille(f"{warn} Hinweise", "knapp"))
        flure: dict[str, int] = {}
        for z in ok:
            flure[zp.flur_text(z.zimmer)] = flure.get(zp.flur_text(z.zimmer), 0) + 1
        if flure:
            # kurz halten (zwei Flure), sonst wird die Zeile im schmalen Fenster zu breit – alle im Tooltip
            text = ", ".join(f"{f.replace('Haus ', 'H').replace(' · ', ' ')}: {n}"
                             for f, n in sorted(flure.items(), key=lambda x: -x[1])[:2])
            lab = label(text + (f" + {len(flure) - 2} Flure" if len(flure) > 2 else ""), "klein")
            lab.setToolTip("<br>".join(f"{f}: {n}" for f, n in sorted(flure.items(), key=lambda x: -x[1])))
            self.zu_status.addWidget(lab)
        angenommen = sum(1 for z in zts if z.bedarf.bis_angenommen)
        if angenommen:
            p = Pille(f"≈ {angenommen}× Abreise angenommen", "neutral")
            p.setToolTip(f"Ohne eingetragene Abreise wird eine übliche Dauer angenommen ({zp.STANDARD_TEXT}). "
                         "Abreise unter Daten & Import eintragen.")
            self.zu_status.addWidget(p)

    def _kennung_fuer_liste(self, liste: date) -> str:
        tage = {b.von for b in (self.stand.bedarf if self.stand else []) if b.liste_anreise == liste}
        return (liste if liste in tage or not tage else min(tage)).isoformat()

    def _person_hinzufuegen(self) -> None:
        from ... import anreiseliste
        from ..dialoge import PersonDialog, erinnerung_abgleichen

        tag = date.fromisoformat(self._anreise_kennung) if self._anreise_kennung else date.today()
        listen = sorted({b.liste_anreise for b in self._bedarf() if b.liste_anreise})
        dialog = PersonDialog(None, self, anreise=listen[0] if listen else tag)
        if not dialog.exec() or dialog.ergebnis is None:
            return
        neu = dialog.ergebnis
        meldung = erinnerung_abgleichen(None, neu)
        anreiseliste.person_speichern(neu)
        self._anreise_kennung = None
        self.z.zimmer_anreise = neu.anreise
        self.z.meldung.emit(*(meldung or (f"{neu.name} zur Anreise am {neu.anreise:%d.%m.%Y} hinzugefügt.", "ok")))
        self.z.listen_geaendert.emit()
        self.neu_laden()

    def _angabe(self, b: zp.Bedarf, **werte) -> None:
        zp.angabe_setzen(b.schluessel, **werte)
        for k, v in werte.items():
            setattr(b, k, v)
        if "geschlecht" in werte:
            b.geschlecht_geschaetzt = False
        self._berechnen()

    def _zimmer(self, b: zp.Bedarf, zid: str | None) -> None:
        if zid:
            self._fest[b.schluessel] = zid
        else:
            self._fest.pop(b.schluessel, None)
        self._berechnen()

    def _uebernehmen(self) -> None:
        n = zp.zuweisungen_speichern(self._zuteilungen)
        ohne = [z.bedarf.schluessel for z in self._zuteilungen if z.zimmer is None]
        zp.zuweisungen_entfernen(set(ohne))
        self.z.meldung.emit(f"{n} Zuweisungen übernommen" + (f", {len(ohne)} ohne Zimmer." if ohne else "."),
                            "ok" if not ohne else "warnung")
        self.neu_laden()

    # ---- Aufgaben ----------------------------------------------------------------------

    def _aufgaben_zaehler(self) -> None:
        """Offene Einträge der nächsten 14 Tage im Reiter anzeigen."""
        from ... import eintragen

        if self.stand is None:
            return
        n = sum(1 for z in eintragen.offen(self.stand.lage, bis=date.today() + timedelta(days=14)) if not z.haken)
        self.tabs.text_setzen(TABS.index("Aufgaben"), f"Aufgaben ({n})" if n else "Aufgaben")

    def _aufgaben_zeigen(self) -> None:
        self._eintragen_zeigen()
        self._facility_zeigen()
        self._engpaesse_zeigen()

    def _facility_zeigen(self) -> None:
        from ... import eintragen

        leeren(self.fc_inhalt)
        heute = date.today()
        # offen aus den letzten 4 Wochen und alles der nächsten 4 Wochen
        checks = [c for c in eintragen.facility_checks(self.stand.lage, heute - timedelta(weeks=4),
                                                       heute + timedelta(weeks=4))
                  if not (c.haken and c.bis < heute)]
        if not checks:
            self.fc_inhalt.addWidget(label(f"Keine Auszüge nach mehr als {round(eintragen.facility_tage() / 30.44)} "
                                           "Monaten in den nächsten 4 Wochen.", "muted", umbruch=True))
            return
        tab = Tabelle(["", "Zimmer", "Auszug", "Aufenthalt", "Wer", "Aufgabe"], ["l", "l", "l", "r", "l", "l"], dehnen=4)
        tab.setTextElideMode(Qt.ElideRight)
        t = theme.T
        zeilen, farben = [], {}
        for i, c in enumerate(checks):
            cb = QCheckBox()
            cb.setChecked(c.haken)
            cb.setToolTip("Facility-Check erledigt")
            cb.toggled.connect(lambda an, c=c: (eintragen.facility_setzen(c, an), self._facility_zeigen()))
            zeilen.append([self._zelle(cb, 10), c.zimmer.removeprefix("GS-"), f"{WOCHENTAGE[c.bis.weekday()]} {c.bis:%d.%m.}",
                           f"{c.monate} Mon.", f"{c.name}" + (f" ({c.massnahme})" if c.massnahme else ""),
                           eintragen.FACILITY_AUFGABE])
            if not c.haken and c.bis <= heute:
                farben[(i, 2)] = t.ueber
            elif c.haken:
                for k in range(1, 6):
                    farben[(i, k)] = t.text_3
        tab.fuellen(zeilen, farben)
        tab.widgets_einpassen()
        tab.hoehe_anpassen(len(zeilen))
        self.fc_inhalt.addWidget(tab)

    def _eintragen_zeigen(self) -> None:
        from ... import eintragen

        leeren(self.ei_inhalt)
        heute = date.today()
        bis = {0: heute + timedelta(days=14), 1: heute + timedelta(weeks=8)}.get(self.ei_zeitraum.index())
        alle = eintragen.offen(self.stand.lage, heute, bis)
        zeilen = [z for z in alle if not (self.ei_fertig.isChecked() and z.haken)]
        offen = sum(1 for z in alle if not z.haken)
        self.ei_info.setText(f"{offen} noch einzutragen, {len(alle) - offen} abgehakt (warten auf den nächsten Gebäudeplan)."
                             if alle else "")
        if not zeilen:
            self.ei_inhalt.addWidget(label("✓ Alles eingetragen – für diesen Zeitraum ist im Belegungssystem nichts "
                                           "nachzutragen.", "muted", umbruch=True))
            self._aufgaben_zaehler()
            return
        tage: dict[date, list] = {}
        for z in zeilen:
            tage.setdefault(z.von, []).append(z)
        for tag, liste in tage.items():
            kopf = QHBoxLayout()
            kopf.setSpacing(8)
            gruppen = sorted({z.massnahme for z in liste if z.massnahme})
            titel = label("", "", umbruch=True)
            kopf.addWidget(titel, 1)
            alle_knopf = knopf("Alle abhaken", "ghost", "haken")
            kopieren = knopf("Kopieren", "ghost", "kopieren", "Zimmer, Name, Maßnahme, Zeitraum für Excel/Notizen kopieren")
            kopf.addWidget(alle_knopf, 0, Qt.AlignTop)
            kopf.addWidget(kopieren, 0, Qt.AlignTop)
            self.ei_inhalt.addLayout(kopf)
            tab = Tabelle(["", "Zimmer", "Name", "Maßnahme", "Zeitraum"], ["l"] * 5, dehnen=2)
            tab.setTextElideMode(Qt.ElideRight)
            kaesten = []
            reihen = []
            for z in liste:
                cb = QCheckBox()
                cb.setChecked(z.haken)
                cb.setToolTip("Im Belegungssystem eingetragen")
                kaesten.append(cb)
                reihen.append([self._zelle(cb, 10), z.zimmer.removeprefix("GS-"), z.name, z.massnahme,
                               f"{z.von:%d.%m.}–{z.bis:%d.%m.%y}"])
            tab.fuellen(reihen)
            tab.widgets_einpassen()
            tab.hoehe_anpassen(len(liste))

            def kopf_text(titel=titel, liste=liste, tag=tag, gruppen=gruppen):
                fertig = sum(1 for z in liste if z.haken)
                titel.setText(f"<b>{WOCHENTAGE[tag.weekday()]} {tag:%d.%m.%Y}</b> · "
                              + (", ".join(gruppen[:3]) + (" …" if len(gruppen) > 3 else "") + " · " if gruppen else "")
                              + f"{fertig} von {len(liste)} eingetragen")

            def haken(an, z, kopf_text=kopf_text):
                z.haken = an
                eintragen.setzen([z], an)
                kopf_text()
                self._aufgaben_zaehler()

            for cb, z in zip(kaesten, liste):
                cb.toggled.connect(lambda an, z=z, haken=haken: haken(an, z))
            alle_knopf.clicked.connect(lambda _=False, kaesten=kaesten: [cb.setChecked(True) for cb in kaesten])
            kopieren.clicked.connect(lambda _=False, liste=liste: self._kopieren(eintragen.kopiertext(liste)))
            kopf_text()
            self.ei_inhalt.addWidget(tab)
        self._aufgaben_zaehler()

    def _kopieren(self, text: str) -> None:
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText(text)
        self.z.meldung.emit(f"{text.count(chr(10)) + 1} Zeilen kopiert.", "ok")

    def _engpaesse_zeigen(self) -> None:
        from ... import eintragen

        wochen = eintragen.engpaesse(self.stand.lage)
        t = theme.T
        farbe = {"ok": t.ok, "knapp": t.knapp, "kritisch": t.ueber}
        zeilen, farben = [], {}
        for r, w in enumerate(wochen):
            stufe = w.gesamtstufe
            text = {"ok": "ok", "knapp": "knapp", "kritisch": "kritisch"}[stufe]
            if stufe != "ok":
                engpass = [n for a, n in (("gesamt", "Zimmer"), ("emr", "EMR"), ("doppel", "Doppelzimmer"))
                           if w.stufe(a) != "ok"]
                text += " – " + ", ".join(engpass)
            zeilen.append([f"KW {w.montag.isocalendar()[1]}", f"{w.montag:%d.%m.}–{w.montag + timedelta(days=6):%d.%m.}",
                           w.gesamt, w.emr, w.doppel, text])
            for c, art in ((2, "gesamt"), (3, "emr"), (4, "doppel")):
                if w.stufe(art) != "ok":
                    farben[(r, c)] = farbe[w.stufe(art)]
            farben[(r, 5)] = farbe[stufe]
        self.eng_tab.fuellen(zeilen, farben)
        self.eng_tab.hoehe_anpassen(len(zeilen))

    # ---- Drucken -------------------------------------------------------------------------

    def _dokument_drucken(self, drucker, html: str, quer: bool) -> None:
        drucken.dokument_drucken(drucker, html, quer)

    def _html_ausgeben(self, html: str, quer: bool, pdf_name: str | None = None) -> bool:
        return drucken.html_ausgeben(self, self.z, html, quer, pdf_name)

    def _wochenblatt(self, pdf: bool) -> None:
        from ... import drucklisten

        montag = self.wb_woche.currentData()
        sonntag = montag + timedelta(days=6)
        stand = f"{self.stand.plan.stand:%d.%m.%Y}" if self.stand.plan and self.stand.plan.stand else ""
        html = drucklisten.wochenblatt_html(self.stand.lage, self._reinigungen_zeitraum(montag, sonntag), montag,
                                            self.wb_namen.isChecked(), stand)
        self._html_ausgeben(html, True, f"Wochenblatt_KW{montag.isocalendar()[1]}_{montag:%Y}.pdf" if pdf else None)

    def _anreise_drucken(self, art: str) -> None:
        from ... import drucklisten

        if art == "anreise":
            if not self._zuteilungen:
                return
            b0 = self._zuteilungen[0].bedarf
            titel = next((t for k, _d, t, _b in self._anreise_liste if k == self._anreise_kennung), "")
            nicht_gespeichert = sum(1 for zt in self._zuteilungen if zt.zimmer
                                    and (self.stand.zugewiesen(zt.bedarf.schluessel) or {}).get("zimmer") != zt.zimmer.id)
            if nicht_gespeichert:
                self.z.meldung.emit(f"Hinweis: {nicht_gespeichert} Zimmer sind noch nicht übernommen – gedruckt wird der "
                                    "angezeigte Vorschlag.", "warnung")
            self._html_ausgeben(drucklisten.anreiseliste_html(
                self._zuteilungen, f"{WOCHENTAGE[b0.von.weekday()]} {b0.von:%d.%m.%Y}" + (f" · {titel}" if titel else "")),
                False)
            return
        liste = drucklisten.schilder(self._zuteilungen)
        if not liste:
            self.z.meldung.emit("Für diese Anreise ist noch kein Zimmer zugeteilt.", "warnung")
            return
        b0 = self._zuteilungen[0].bedarf
        titel = next((t for k, _d, t, _b in self._anreise_liste if k == self._anreise_kennung), "")
        if art == "schilder":
            self._html_ausgeben(drucklisten.zimmerschilder_html(liste), True)
        else:
            self._html_ausgeben(drucklisten.schluesselliste_html(liste, f"Anreise {b0.von:%d.%m.%Y}"
                                                                 + (f" · {titel}" if titel else "")), True)

    # ---- Zeitstrahl: geplante Zuweisung per Ziehen verschieben ------------------------------

    def _zs_verschieben(self, person: str, von: str, nach: str) -> None:
        if self.stand is None:
            return
        fehler, hinweis, partner = zp.verschieben_pruefen(self.stand, person, nach)
        if fehler:
            QMessageBox.warning(self, "Verschieben nicht möglich", fehler)
            return
        b = next(x for x in self.stand.bedarf if x.schluessel == person)
        z_neu = self.stand.lage.zimmer[nach]
        text = (f"{b.name} ({b.von:%d.%m.} – {b.bis:%d.%m.%Y}) von Zimmer {von.removeprefix('GS-')} "
                f"nach {z_neu.kurz} verschieben?")
        if hinweis:
            text += f"\n\nAchtung – Ausnahme: {hinweis}"
        text += "\n\nDanach im Belegungssystem umbuchen (steht unter Aufgaben → Eintragen)."
        mit: list = []
        if partner:
            ohne = frozenset({person} | {x.schluessel for x in partner})
            passt_beide = self.stand.lage.freie_betten(nach, b.von, b.bis, ohne) >= 1 + len(partner)
            box = QMessageBox(QMessageBox.Question, "Zimmer verschieben",
                              text + f"\n\nDZ-Partner laut Liste: {', '.join(x.name for x in partner)}.", parent=self)
            beide = box.addButton("Beide verschieben", QMessageBox.AcceptRole) if passt_beide else None
            allein = box.addButton(f"Nur {b.name.split(',')[0]}", QMessageBox.AcceptRole)
            box.addButton("Abbrechen", QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() not in (beide, allein) or box.clickedButton() is None:
                return
            if box.clickedButton() is beide:
                mit = partner
        elif QMessageBox.question(self, "Zimmer verschieben", text) != QMessageBox.Yes:
            return
        zp.zuweisungen_speichern([zp.Zuteilung(x, z_neu) for x in [b] + mit], "Zeitstrahl verschoben")
        namen = ", ".join(x.name for x in [b] + mit)
        self.z.meldung.emit(f"{namen} nach {z_neu.kurz} verschoben.", "warnung" if hinweis else "ok")
        self.neu_laden()

    # ---- Zurücknehmen und Konflikte -----------------------------------------------------

    def _kommende_uwt(self) -> set[str]:
        heute = date.today()
        return {b.schluessel for b in self.stand.bedarf
                if b.gruppe == "UWT" and b.von > heute and self.stand.zugewiesen(b.schluessel)}

    def _zurueck_menue(self) -> None:
        geplant = [b for b in self._bedarf() if self.stand.zugewiesen(b.schluessel)]
        self.m_anreise.setText(f"Planung dieser Anreise zurücknehmen ({len(geplant)} Personen)")
        self.m_anreise.setEnabled(bool(geplant))
        n = len(self._kommende_uwt())
        self.m_uwt_weg.setText(f"Alle kommenden UWT-Planungen zurücknehmen ({n} Personen)")
        self.m_uwt_weg.setEnabled(bool(n))

    def _anreise_zuruecknehmen(self) -> None:
        geplant = {b.schluessel for b in self._bedarf() if self.stand.zugewiesen(b.schluessel)}
        if not geplant or QMessageBox.question(
                self, "Planung zurücknehmen", f"Die gespeicherten Zimmer von {len(geplant)} Personen dieser Anreise "
                "entfernen? Die Zimmer sind danach wieder frei; der Vorschlag bleibt sichtbar und kann neu "
                "übernommen werden.") != QMessageBox.Yes:
            return
        n = zp.planung_zuruecknehmen(geplant)
        self.z.meldung.emit(f"Planung zurückgenommen: {n} Personen ohne Zimmer.", "ok")
        self.neu_laden()

    def _uwt_zuruecknehmen(self) -> None:
        personen = self._kommende_uwt()
        if not personen or QMessageBox.question(
                self, "UWT-Planungen zurücknehmen", f"Die Zimmer aller kommenden UWT ({len(personen)} Personen) "
                "entfernen? Sie werden danach nicht wieder automatisch zugeteilt – über „Alle kommenden UWT neu "
                "automatisch zuteilen“ geht das jederzeit wieder.") != QMessageBox.Yes:
            return
        n = zp.planung_zuruecknehmen(personen)
        self.z.meldung.emit(f"UWT-Planungen zurückgenommen: {n} Personen.", "ok")
        self.neu_laden()

    def _uwt_neu(self) -> None:
        if QMessageBox.question(
                self, "UWT neu zuteilen", "Alle kommenden UWT-Planungen verwerfen (auch Änderungen von Hand) und neu "
                "automatisch zuteilen – DZ-Paare zusammen?") != QMessageBox.Yes:
            return
        neu = zp.uwt_neu_zuteilen(self.stand)
        self.z.meldung.emit(f"UWT neu zugeteilt: {len(neu)} Personen.", "ok")
        self.neu_laden()

    def _konflikte_loesen(self) -> None:
        personen = {k.person for k in getattr(self, "_konflikte", [])}
        if not personen:
            return
        neu, ohne = zp.neu_planen(self.stand, personen)
        text = f"Neu geplant: {len(neu)} Personen in freien Zimmern."
        if ohne:
            text += f" Kein freies Zimmer für {', '.join(b.name for b in ohne[:4])}" + (" …" if len(ohne) > 4 else "") + \
                    " – bitte unter Zuteilen von Hand festlegen."
        self.z.meldung.emit(text, "warnung" if ohne else "ok")
        self.neu_laden()

    # ---- Excel -------------------------------------------------------------------------

    def _speicherort(self, vorschlag: str) -> Path | None:
        start = speicher.einstellungen().get("export_ordner") or str(Path.home())
        pfad, _ = QFileDialog.getSaveFileName(self, "Excel speichern", str(Path(start) / vorschlag), "Excel (*.xlsx)")
        if not pfad:
            return None
        speicher.einstellung_setzen("export_ordner", str(Path(pfad).parent))
        return Path(pfad if pfad.lower().endswith(".xlsx") else pfad + ".xlsx")

    def _excel(self) -> None:
        if not self._zuteilungen:
            return
        b0 = self._zuteilungen[0].bedarf
        titel = next((t for k, _d, t, _b in self._anreise_liste if k == self._anreise_kennung), "")
        pfad = self._speicherort(f"Zimmerliste_{b0.von:%Y-%m-%d}.xlsx")
        if pfad:
            self._excel_schreiben(pfad, f"Zimmerliste Anreise {b0.von:%d.%m.%Y}" + (f" – {titel}" if titel else ""),
                                  self._zuteilungen, b0.von)

    def _excel_frei(self) -> None:
        tag = self.tag.datum()
        pfad = self._speicherort(f"Freie_Zimmer_{tag:%Y-%m-%d}.xlsx")
        if pfad:
            self._excel_schreiben(pfad, f"Belegung am {tag:%d.%m.%Y}", [], tag)

    def _excel_schreiben(self, pfad: Path, titel: str, zuteilungen, tag: date) -> None:
        try:
            zimmerexport.exportieren(pfad, titel, zuteilungen, self.stand.lage, tag)
        except PermissionError:
            self.z.meldung.emit("Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", "fehler")
            return
        self.z.meldung.emit(f"Gespeichert: {pfad.name}", "ok")
        import os
        import sys

        if sys.platform == "win32":
            os.startfile(str(pfad))

    # ================================================================== Zeitstrahl

    def _monat_wechseln(self, schritt: int) -> None:
        if schritt == 0:
            self._monat = date.today().replace(day=1)
        else:
            m = self._monat.month - 1 + schritt
            self._monat = date(self._monat.year + m // 12, m % 12 + 1, 1)
        self._zeitstrahl_zeigen()

    def _zeitstrahl_zeigen(self) -> None:
        if self.stand is None:
            return
        von = self._monat
        naechster = date(von.year + von.month // 12, von.month % 12 + 1, 1)
        bis = naechster - timedelta(days=1)
        self.monat_text.setText(f"{MONATE[von.month - 1]} {von.year}")
        i = self.zs_haus.index()
        zimmer = [z for z in self.stand.zimmer if z.aktiv and (i == 5 or z.haus == HAEUSER[i])]
        suche = self.zs_suche.text().strip().lower()
        gruppen, modus = self.zs_gruppe.auswahl(), self.zs_modus.currentData()
        if gruppen and modus == "darf":
            zimmer = [z for z in zimmer if any(zp.erlaubt(z, g) for g in gruppen)]
        zeilen = zp.zeitstrahl(self.stand.lage, zimmer, von, bis)
        if gruppen and modus == "wohnt":
            zeilen = [(z, spuren) for z, spuren in zeilen
                      if any(zp.belegung_gruppe(bk.belegung) in gruppen for spur in spuren for bk in spur)]
        self.zeitstrahl.gruppen = gruppen if modus == "wohnt" else set()
        if self._zs_arten:
            zeilen = [(z, spuren) for z, spuren in zeilen
                      if any(bk.art in self._zs_arten for spur in spuren for bk in spur)]
        self.zeitstrahl.arten = set(self._zs_arten)
        if suche:
            zeilen = [(z, spuren) for z, spuren in zeilen
                      if suche in z.id.lower() or suche in z.nr.lower()
                      or any(suche in bk.text.lower() for spur in spuren for bk in spur)]
        self.zeitstrahl.setzen(zeilen, von, bis)
        from ..zeitstrahl import muster

        from PySide6.QtGui import QIcon

        leeren(self.zs_legende)
        # Legende = Filter: anklicken zeigt nur Zimmer mit dieser Art (mehrere kombinierbar)
        for art, text in (("belegt", "belegt"), ("geplant", "geplant (Zimmerplan)"),
                          ("pivot", "belegt laut Zimmer-Pivot"), ("gesperrt", "gesperrt / Renovierung")):
            b = knopf(text, "chip")
            b.setCheckable(True)
            b.setChecked(art in self._zs_arten)
            b.setIcon(QIcon(muster(art)))
            b.setIconSize(muster(art).size() / max(muster(art).devicePixelRatio(), 1))
            b.setToolTip(f"Nur Zimmer mit „{text}“ zeigen – nochmal klicken zum Aufheben")
            b.clicked.connect(lambda an, a=art: self._zs_art_umschalten(a, an))
            self.zs_legende.addWidget(b)
        if self._zs_arten:
            alle = knopf("Filter aufheben", "ghost")
            alle.clicked.connect(lambda: self._zs_art_umschalten(None, False))
            self.zs_legende.addWidget(alle)
        if self.zeitstrahl.gruppen:
            namen = ", ".join(zp.GRUPPE_LABEL.get(g, g) for g in zp.GRUPPEN if g in self.zeitstrahl.gruppen)
            self.zs_legende.addWidget(label(f"blass = andere Gruppen als {namen}", "klein"))
        self.zs_anzahl.setText(f"{len(zeilen)} Zimmer")

    def _zs_art_umschalten(self, art: str | None, an: bool) -> None:
        if art is None:
            self._zs_arten.clear()
        elif an:
            self._zs_arten.add(art)
        else:
            self._zs_arten.discard(art)
        self._zeitstrahl_zeigen()

    # ================================================================== Reinigung

    def _woche_wechseln(self, richtung: int) -> None:
        self._woche = date.today() if richtung == 0 else self._woche + timedelta(days=7 * richtung)
        self._reinigung_zeigen()

    def _reinigung_daten(self):
        from ... import reinigungsliste as rl

        von, bis = rl.woche(self._woche)
        zpv = self.stand.zimmer_pivot if self.stand else None
        am_tag = self.rg_anreisetag.isChecked()
        rs = zp.reinigungen(self.stand.lage, von, bis, zpv.zeitraum[1] if zpv else None,
                            zpv.zeitraum[0] if zpv else None, am_tag) if self.stand else []
        return rl, von, bis, rs

    def _anreisen_ohne_zimmer(self, von: date, bis: date) -> list:
        """Anreisen, deren Einzugsreinigung in die Woche fiele, die aber noch kein Zimmer haben."""
        if self.stand is None:
            return []
        am_tag = self.rg_anreisetag.isChecked()
        # wer schon im Gebäudeplan gebucht ist, hat seine Einzugsreinigung bereits auf der Liste
        gebucht = {(b.name.strip().lower(), b.von) for bs in self.stand.lage.belegungen.values() for b in bs}
        return [b for b in self.stand.bedarf if not self.stand.zugewiesen(b.schluessel)
                and (b.name.strip().lower(), b.von) not in gebucht
                and von <= zp.einzug_tag(b.von, None, am_tag) <= bis]

    def _prio_farbe(self, p: int) -> str:
        t = theme.T
        return {0: t.ueber, 1: t.ueber, 2: t.knapp, 3: t.accent, 9: t.text_3}.get(p, t.text_2)

    def _haken(self, r, erledigt_an: bool) -> QWidget:
        """Abhak-Kästchen für eine Reinigung (zentriert in der Tabellenzelle)."""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        cb = QCheckBox()
        cb.setChecked(erledigt_an)
        cb.setToolTip("Reinigung erledigt – nochmal klicken nimmt das Häkchen zurück")
        cb.setCursor(Qt.PointingHandCursor)
        cb.toggled.connect(lambda an, r=r: self._reinigung_abhaken(r, an))
        h.addWidget(cb, 0, Qt.AlignCenter)
        return w

    @staticmethod
    def _reinigung_tabelle_einpassen(tab, dehnbar: tuple[int, ...]) -> None:
        """Lange Spalten (Auszug, Einzug) teilen sich den Platz und kürzen mit „…“ – keine Bildlaufleiste;
        der volle Text steht im Tooltip."""
        from PySide6.QtWidgets import QHeaderView

        tab.widgets_einpassen()
        tab.setTextElideMode(Qt.ElideRight)
        tab.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        kh = tab.horizontalHeader()
        for c in range(tab.columnCount()):
            if c in dehnbar:
                kh.setSectionResizeMode(c, QHeaderView.Stretch)
            for r in range(tab.rowCount()):
                item = tab.item(r, c)
                if item is not None and c in dehnbar:
                    item.setToolTip(item.text())

    def _reinigung_abhaken(self, r, an: bool) -> None:
        from PySide6.QtCore import QTimer

        from ... import reinigungsliste as rl

        rl.erledigt_setzen(r, an)
        self.z.meldung.emit(f"Zimmer {r.zimmer.haus}-{r.zimmer.nr}: Reinigung "
                            + ("erledigt." if an else "wieder offen."), "ok")
        self.z.termine_geaendert.emit()            # Hinweise/Zähler in der Seitenleiste aktualisieren
        QTimer.singleShot(0, self._reinigung_zeigen)

    def _reinigung_zeigen(self) -> None:
        if self.stand is None:
            return
        rl, von, bis, rs = self._reinigung_daten()
        heute = date.today()
        fertig = rl.erledigt()
        self.rg_titel.setText(rl.titel(von, bis).replace("Reinigungsliste ", ""))
        leeren(self.rg_wichtig)
        leeren(self.rg_tage)

        # --- Dringendes (unabhängig von der gewählten Woche) ---------------------------------
        # Konflikte: heute/morgen kommt jemand, Zimmer nicht abgehakt. Darunter nur, was aus FRÜHEREN Wochen
        # noch offen ist – alles aus dieser Woche steht unten im jeweiligen Tag (keine doppelten Zeilen).
        diese_woche = rl.woche(heute)[0]
        nah = [r for r in self._reinigungen_zeitraum(heute - timedelta(days=14), heute + timedelta(days=3))
               if rl.prioritaet(r, heute, fertig) <= 4]
        kon = rl.konflikte(nah, heute, fertig)
        offen = sorted((r for r in nah if r.tag < diese_woche),
                       key=lambda r: (rl.prioritaet(r, heute, fertig), r.naechste_anreise or r.tag, r.zimmer.id))
        if kon:
            h = Hinweis(f"{len(kon)} Zimmer noch nicht gereinigt, obwohl heute/morgen jemand einzieht: "
                        + "; ".join(rl.konflikt_text(r) for r in kon[:3]) + (" …" if len(kon) > 3 else ""), "fehler")
            self.rg_wichtig.addWidget(h)
        if offen:
            karte = Karte("Noch offen aus den Vorwochen", "Nicht abgehakte Reinigungen vor dieser Woche – abhaken, "
                                                          "sobald erledigt.")
            tab = Tabelle(["✓", "Zimmer", "Auszug", "Sauber bis spätestens", "Status"],
                          ["l", "l", "l", "l", "l"], dehnen=3)
            zeilen, farben = [], {}
            for i, r in enumerate(offen):
                p = rl.prioritaet(r, heute, fertig)
                zeilen.append([self._haken(r, False), r.zimmer.kurz, rl.auszug_datum(r), rl.frist_text(r),
                               rl.prio_text(r, heute, fertig)])
                farben[(i, 4)] = self._prio_farbe(p)
            tab.fuellen(zeilen, farben)
            self._reinigung_tooltips(tab, offen)
            self._reinigung_tabelle_einpassen(tab, (3,))
            tab.hoehe_anpassen(10)
            karte.inhalt.addWidget(tab)
            self.rg_wichtig.addWidget(karte)

        # --- Woche --------------------------------------------------------------------------
        ohne = self._anreisen_ohne_zimmer(von, bis)
        if ohne:
            h = Hinweis(f"{len(ohne)} Anreise(n) in dieser Zeit haben noch kein Zimmer – sie fehlen auf der Liste. "
                        "Erst unter „Zuteilen“ übernehmen.", "warnung", "Zu Zuteilen")
            h.knopf.clicked.connect(lambda: (self.tabs.setzen(0), self._tab(0)))
            self.rg_tage.addWidget(h)
        n_fertig = sum(1 for r in rs if rl.prioritaet(r, heute, fertig) == 9)
        self.rg_info.setText((rl.zaehlung(rs) + f" · {n_fertig} erledigt") if rs else
                             "In dieser Woche zieht niemand aus und kein leeres Zimmer muss vorbereitet werden.")
        ausblenden = self.rg_ausblenden.isChecked()
        t = theme.T
        liste = rl.sortiert(rs, heute, fertig)
        if ausblenden:
            liste = [r for r in liste if rl.prioritaet(r, heute, fertig) != 9]
        if not rs:
            return
        karte = Karte("Zimmer reinigen – nach Frist", "Sauber bis spätestens = letzter Werktag vor der nächsten Anreise "
                                                      "(Sa/So wird nicht gereinigt). "
                                                      "Maus auf die Zeile: wer auszieht und wer kommt."
                      + (" – alles erledigt ✓" if not liste else ""))
        if liste:
            tab = Tabelle(["✓", "Zimmer", "Auszug", "Sauber bis spätestens", "Status"],
                          ["l", "l", "l", "l", "l"], dehnen=3)
            zeilen, farben = [], {}
            for i, r in enumerate(liste):
                p = rl.prioritaet(r, heute, fertig)
                zeilen.append([self._haken(r, p == 9), r.zimmer.kurz, rl.auszug_datum(r), rl.frist_text(r),
                               ("Facility-Check · " if rl.facility(r) else "") + rl.prio_text(r, heute, fertig)])
                farben[(i, 4)] = self._prio_farbe(p)
                if p == 9:
                    for c in range(1, 4):
                        farben[(i, c)] = t.text_3
                elif r.knapp:
                    farben[(i, 3)] = t.ueber            # gleich nach Auszug, am Anreisetag oder Wochenende
            tab.fuellen(zeilen, farben)
            self._reinigung_tooltips(tab, liste)
            self._reinigung_tabelle_einpassen(tab, (3,))
            tab.hoehe_anpassen(len(liste))
            karte.inhalt.addWidget(tab)
        self.rg_tage.addWidget(karte)

    def _reinigung_tooltips(self, tab, liste) -> None:
        from ... import reinigungsliste as rl

        for r, x in enumerate(liste):
            text = f"{x.zimmer.kurz} · {zp.flur_text(x.zimmer)}\n" + rl.details(x, True)
            for c in range(1, tab.columnCount()):
                if tab.item(r, c):
                    tab.item(r, c).setToolTip(text)

    def _reinigungen_zeitraum(self, von: date, bis: date) -> list:
        zpv = self.stand.zimmer_pivot if self.stand else None
        return zp.reinigungen(self.stand.lage, von, bis, zpv.zeitraum[1] if zpv else None,
                              zpv.zeitraum[0] if zpv else None, self.rg_anreisetag.isChecked())

    def _reinigung_drucken(self) -> None:
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter

        drucker = QPrinter(QPrinter.HighResolution)
        if QPrintDialog(drucker, self).exec() != QDialog.Accepted:
            return
        self._reinigung_ausgeben(drucker)
        self.z.meldung.emit("Reinigungsliste an den Drucker geschickt.", "ok")

    def _reinigung_pdf(self) -> None:
        from PySide6.QtPrintSupport import QPrinter

        rl, von, _bis, _rs = self._reinigung_daten()
        start = speicher.einstellungen().get("export_ordner") or str(Path.home())
        pfad, _ = QFileDialog.getSaveFileName(self, "PDF speichern",
                                              str(Path(start) / f"Reinigungsliste_KW{von.isocalendar()[1]}_{von:%Y}.pdf"),
                                              "PDF (*.pdf)")
        if not pfad:
            return
        speicher.einstellung_setzen("export_ordner", str(Path(pfad).parent))
        drucker = QPrinter(QPrinter.HighResolution)
        drucker.setOutputFormat(QPrinter.PdfFormat)
        drucker.setOutputFileName(pfad if pfad.lower().endswith(".pdf") else pfad + ".pdf")
        self._reinigung_ausgeben(drucker)
        self.z.meldung.emit(f"PDF gespeichert: {Path(pfad).name}", "ok")

    def _reinigung_ausgeben(self, drucker) -> None:
        rl, von, bis, rs = self._reinigung_daten()
        stand = f"{self.stand.plan.stand:%d.%m.%Y}" if self.stand and self.stand.plan and self.stand.plan.stand else ""
        self._dokument_drucken(drucker, rl.html_text(rs, von, bis, False, stand,
                                                     len(self._anreisen_ohne_zimmer(von, bis)), date.today(),
                                                     rl.erledigt()), True)

    def _reinigung_excel(self) -> None:
        rl, von, bis, rs = self._reinigung_daten()
        pfad = self._speicherort(f"Reinigungsliste_KW{von.isocalendar()[1]}_{von:%Y}.xlsx")
        if pfad:
            rl.excel_speichern(pfad, rs, von, bis, False)
            self.z.meldung.emit(f"Excel gespeichert: {pfad.name}", "ok")

    # ================================================================== Häuser

    def _filter_setzen(self, status: str | None) -> None:
        self._haus_filter = status
        if status in self.filter_knoepfe:
            self.filter_knoepfe[status].setChecked(True)
        self._haeuser_zeigen()

    def _haeuser_zeigen(self) -> None:
        if self.stand is None:
            return
        leeren(self.haeuser)
        farben = _status_farben()
        leeren(self.h_legende)            # Farblegende (bei jedem Aufbau – passt sich dem Design an)
        for status, text in (("frei", "frei"), ("teilweise", "teilweise frei (Doppelzimmer, 1 Bett frei)"),
                             ("belegt", "belegt"), ("geplant", "geplant (Zimmerplan)"), ("gesperrt", "gesperrt")):
            bg, fg = farben[status]
            muster = label(text, "klein")
            muster.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:5px; padding:2px 7px;")
            self.h_legende.addWidget(muster)
        st, tag = self.stand, self.tag.datum()
        haeuser: dict[str, list[zp.Zimmer]] = {}
        for z in st.zimmer:
            if z.aktiv:
                haeuser.setdefault(z.haus, []).append(z)
        if not haeuser:
            self.haeuser.addWidget(Leer("haus", "Kein Gebäudeplan", "Unter „Quellen“ den Gebäudeplan (.docx) importieren."))
            return
        status_je = {z.id: st.lage.status_am(z.id, tag) for z in st.zimmer if z.aktiv}
        zaehler: dict[str, int] = {}
        for s, _b in status_je.values():
            zaehler[s] = zaehler.get(s, 0) + 1
        for schluessel, b in self.filter_knoepfe.items():
            basis = {None: "Alle", "frei": "Frei", "teilweise": "Teilweise frei", "belegt": "Belegt",
                     "geplant": "Geplant", "gesperrt": "Gesperrt"}[schluessel]
            b.setText(basis if schluessel is None else f"{basis} ({zaehler.get(schluessel, 0)})")
        gruppen, modus = self.h_gruppe.auswahl(), self.h_modus.currentData()
        gruppen_je = {z.id: zp.gruppen_am(st.lage, z.id, tag) for z in st.zimmer if z.aktiv}

        def passt_gruppe(z, auswahl: set | None = None) -> bool:
            auswahl = gruppen if auswahl is None else auswahl
            if not auswahl:
                return True
            if modus == "wohnt":
                return bool(auswahl & gruppen_je[z.id])
            return any(zp.erlaubt(z, g) for g in auswahl)

        # Anzahl je Gruppe (unter dem gewählten Status) im Auswahlmenü anzeigen
        aktive = [z for z in st.zimmer if z.aktiv and self._haus_filter in (None, status_je[z.id][0])]
        self.h_gruppe.anzahl_setzen({g: sum(1 for z in aktive if passt_gruppe(z, {g})) for g in zp.GRUPPEN})
        gefiltert = self._haus_filter is not None or bool(gruppen)
        gezeigt = 0
        for haus, zimmer in haeuser.items():
            sichtbar = [z for z in zimmer if self._haus_filter in (None, status_je[z.id][0]) and passt_gruppe(z)]
            if not sichtbar:
                continue
            gezeigt += 1
            frei = sum(1 for z in zimmer if status_je[z.id][0] in ("frei", "teilweise"))
            karte = Karte(f"Haus {haus}", f"{len(zimmer)} Zimmer · {frei} frei am {tag:%d.%m.%Y}"
                          + (f" · {len(sichtbar)} angezeigt" if gefiltert else ""))
            karte.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)   # umbrechende Etagen nicht abschneiden
            gitter = QGridLayout()
            gitter.setHorizontalSpacing(18)
            gitter.setVerticalSpacing(10)
            etagen = sorted({z.etage for z in sichtbar}, key=zp._etage_sort, reverse=True)
            flure = [None]          # West/Ost nicht anzeigen – je Etage alle Zimmer nach Nummer
            for r, e in enumerate(etagen, start=1):
                gitter.addWidget(label(zp.etage_text(e), "fett"), r, 0, Qt.AlignTop)
                for c, f in enumerate(flure):
                    feld = QWidget()
                    fl = FlowLayout(feld, abstand=4)
                    for z in sorted((z for z in sichtbar if z.etage == e), key=lambda z: z.nummer):
                        status, bel = status_je[z.id]
                        bg, fg = farben[status]
                        merk = "".join(k for k, an in (("D", z.betten > 1), ("T", z.tiere), ("M", z.nur_maenner), ("G", z.gaeste)) if an)
                        kachel = QPushButton(f"{z.nr} {merk}".strip())
                        kachel.setCursor(Qt.PointingHandCursor)
                        kachel.setStyleSheet(f"QPushButton {{ background:{bg}; color:{fg}; border:none; border-radius:6px; "
                                             f"padding:4px 7px; font-size:11.5px; }} QPushButton:hover {{ border:1px solid {theme.T.accent}; }}")
                        kachel.setToolTip(self._tooltip(z, status, bel, tag))
                        kachel.clicked.connect(lambda _=False, zid=z.id: self._zimmer_details(zid))
                        fl.addWidget(kachel)
                    gitter.addWidget(feld, r, c + 1)
            for c in range(len(flure)):
                gitter.setColumnStretch(c + 1, 1)
            karte.inhalt.addLayout(gitter)
            self.haeuser.addWidget(karte)
        if not gezeigt:
            self.haeuser.addWidget(Leer("haus", "Keine Zimmer für diese Auswahl",
                                        f"Am {tag:%d.%m.%Y} passt kein Zimmer zu Status und Gruppe – Filter ändern "
                                        "oder anderen Tag wählen."))

    def _tooltip(self, z: zp.Zimmer, status: str, bel, tag: date) -> str:
        zeilen = [f"<b>{z.id}</b> · {zp.flur_text(z)} · {STATUS_TEXT[status]}"]
        for b in bel:
            if b.art == "freigabe":
                continue
            text, _art = zp.balken_text(b)
            zeilen.append(f"{text} bis {b.bis:%d.%m.%Y}")
        if status in ("frei", "teilweise"):
            bis = self.stand.lage.frei_bis(z.id, tag)
            zeilen.append(f"frei bis {bis:%d.%m.%Y}" if bis else "frei ohne Folgebelegung")
        zeilen.append("<i>Klicken für Details</i>")
        return "<br>".join(zeilen)

    def _zimmer_details(self, zid: str) -> None:
        if self.stand and zid in self.stand.lage.zimmer:
            ZimmerDialog(self.stand, zid, self).exec()

    # ================================================================== Stammdaten

    def _stamm_zeigen(self) -> None:
        haus = HAEUSER[self.stamm_haus.index()]
        self._stamm_zimmer = [z for z in self.stand.zimmer if z.haus == haus]
        tab = self.stamm
        tab.blockSignals(True)
        tab.setRowCount(len(self._stamm_zimmer))
        for r, z in enumerate(self._stamm_zimmer):
            for c, v in enumerate([z.id, zp.etage_text(z.etage), z.flur, str(z.betten)]):
                item = QTableWidgetItem(v)
                if c in (0, 1):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tab.setItem(r, c, item)
            for c, an in ((4, z.nur_maenner), (5, z.tiere), (6, z.gaeste), (7, z.aktiv)):
                item = QTableWidgetItem("")
                item.setFlags((item.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
                item.setCheckState(Qt.Checked if an else Qt.Unchecked)
                tab.setItem(r, c, item)
            tab.setItem(r, 8, QTableWidgetItem(z.notiz))
        tab.blockSignals(False)
        tab.hoehe_anpassen(26)

    def _stamm_speichern(self) -> None:
        tab = self.stamm
        alle = {z.id: z for z in self.stand.zimmer}
        for r, z in enumerate(self._stamm_zimmer):
            ziel = alle[z.id]
            ziel.flur = tab.item(r, 2).text().strip()
            try:
                ziel.betten = max(1, int(tab.item(r, 3).text()))
            except ValueError:
                pass
            ziel.nur_maenner = tab.item(r, 4).checkState() == Qt.Checked
            ziel.tiere = tab.item(r, 5).checkState() == Qt.Checked
            ziel.gaeste = tab.item(r, 6).checkState() == Qt.Checked
            ziel.aktiv = tab.item(r, 7).checkState() == Qt.Checked
            ziel.notiz = tab.item(r, 8).text().strip() if tab.item(r, 8) else ""
        zp.stammdaten_speichern(list(alle.values()), self.stand.plan)
        self.z.meldung.emit("Zimmer-Stammdaten gespeichert.", "ok")
        self.neu_laden()

    # ================================================================== Quellen

    def _protokoll_zeigen(self, anzahl: int | None = None) -> None:
        from ... import protokoll

        self._prot_anzahl = anzahl or self._prot_anzahl
        alle = protokoll.laden()
        zeilen = []
        for e in alle[:self._prot_anzahl]:
            alt, neu = e.get("alt", "").removeprefix("GS-"), e.get("neu", "").removeprefix("GS-")
            zimmer = f"{alt} → {neu}" if alt and neu else (neu or alt)
            zeilen.append([datetime.fromisoformat(e["zeit"]).strftime("%d.%m. %H:%M"), e.get("aktion", ""),
                           e.get("name", ""), zimmer, e.get("quelle", ""), e.get("wer", "")])
        self.prot_tab.fuellen(zeilen)
        self.prot_tab.hoehe_anpassen(12)
        self.prot_tab.setVisible(bool(zeilen))
        self.prot_mehr.setVisible(len(alle) > self._prot_anzahl)

    def _quellen_zeigen(self) -> None:
        self._protokoll_zeigen()
        st = self.stand
        heute = date.today()
        if st.plan is None:
            self.plan_text.setText(f"Noch kein Plan importiert – die {len(st.zimmer)} Zimmer sind mitgeliefert, die Belegung "
                                   "fehlt aber. Neueste Plan-Datei (.docx) in den Ordner „Gebaeudeplan“ legen oder "
                                   "importieren.")
        else:
            stand = f"Stand {st.plan.stand:%d.%m.%Y}" if st.plan.stand else "Stand unbekannt"
            aktiv = [z for z in st.zimmer if z.aktiv]
            self.plan_text.setText(f"<b>{st.plan.datei}</b> · {stand}<br>{len(aktiv)} Zimmer mit "
                                   f"{sum(z.betten for z in aktiv)} Betten in Haus 2, 3.1, 3.2, 3.3 und 6 "
                                   f"(inkl. {sum(1 for z in aktiv if z.gaeste)} Gästezimmer)."
                                   + ("<br>" + "<br>".join(st.plan.hinweise[:2]) if st.plan.hinweise else "")
                                   + "<br>Aktualisieren: Word-Datei im Ordner „Gebaeudeplan“ speichern (wird automatisch "
                                   "übernommen) – oder im Belegungssystem alles kopieren und „Aus Zwischenablage einfügen“.")
        zpv = st.zimmer_pivot
        if zpv is None:
            self.pivot_text.setText("Noch nicht importiert (optional). Ergänzt gebuchte Tage, die im Gebäudeplan fehlen.")
        else:
            extra = {zid for zid, bs in st.lage.belegungen.items() for b in bs if b.name == zp.PIVOT_NAME and b.bis >= heute}
            stand = f"Stand {zpv.stand:%d.%m.%Y}" if zpv.stand else "Stand unbekannt"
            self.pivot_text.setText(f"<b>{zpv.datei}</b> · {stand}<br>{zpv.zimmer} Zimmer, {zpv.zeitraum[0]:%d.%m.%Y} – "
                                    f"{zpv.zeitraum[1]:%d.%m.%Y}<br>"
                                    + (f"<b>{len(extra)} Zimmer</b> mit Buchungen, die im Gebäudeplan fehlen – im Zeitstrahl "
                                       "lila." if extra else "Stimmt mit dem Gebäudeplan überein."))

    def _plan_importieren(self) -> None:
        start = speicher.einstellungen().get("import_ordner_gebaeudeplan") or str(Path.home())
        pfad, _ = QFileDialog.getOpenFileName(self, "Gebäudeplan wählen", start, "Word (*.docx);;Alle Dateien (*)")
        if not pfad:
            return
        speicher.einstellung_setzen("import_ordner_gebaeudeplan", str(Path(pfad).parent))
        try:
            plan = gebaeudeplan.lesen(Path(pfad))
        except Exception as exc:
            self.z.meldung.emit(f"Gebäudeplan konnte nicht gelesen werden: {exc}", "fehler")
            return
        kennung = None
        try:      # Kopie in den Eingangsordner – dann gilt diese Datei als aktueller Stand
            import shutil

            ziel = gebaeudeplan.eingangsordner() / Path(pfad).name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            if ziel.resolve() != Path(pfad).resolve():
                shutil.copy2(pfad, ziel)
            kennung = {"pfad": ziel.name, "geaendert": int(ziel.stat().st_mtime)}
        except OSError:
            pass
        gebaeudeplan.speichern(plan, kennung)
        belegt = sum(1 for b in plan.belegungen if b.art == "belegt")
        self.z.meldung.emit(f"Gebäudeplan importiert: {len(plan.zimmer)} Zimmer, {belegt} Belegungen.", "ok")
        self.neu_laden()

    def _plan_einfuegen(self) -> None:
        from PySide6.QtWidgets import QApplication, QMessageBox

        mime = QApplication.clipboard().mimeData()
        text = mime.text() if mime and mime.hasText() else ""
        html = mime.html() if mime and mime.hasHtml() else ""
        try:
            plan = gebaeudeplan.aus_zwischenablage(text, html)
        except ValueError as exc:
            self.z.meldung.emit(str(exc), "fehler")
            return
        belegt = sum(1 for b in plan.belegungen if b.art == "belegt")
        gesperrt = sum(1 for b in plan.belegungen if b.art == "gesperrt")
        frage = QMessageBox.question(
            self, "Gebäudeplan einfügen",
            f"Erkannt: {len(plan.zimmer)} Zimmer mit {sum(z.betten for z in plan.zimmer)} Betten, "
            f"{belegt} Belegungen, {gesperrt} Sperrungen.\n\nAls aktuellen Gebäudeplan (Stand heute) übernehmen?")
        if frage != QMessageBox.Yes:
            return
        speicher.schreiben(f"{speicher.IMPORT_ORDNER}/gebaeudeplan_eingefuegt.json",
                           {"text": text, "html": html[:2_000_000]})       # Rohdaten zur Nachkontrolle
        gebaeudeplan.speichern(plan, {"pfad": "Zwischenablage", "geaendert": 0})
        self.z.meldung.emit(f"Gebäudeplan eingefügt: {len(plan.zimmer)} Zimmer, {belegt} Belegungen.", "ok")
        self.neu_laden()

    def _eingang_oeffnen(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        ordner = gebaeudeplan.eingangsordner()
        ordner.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ordner)))

    def _pivot_importieren(self) -> None:
        from ... import zimmerpivot

        start = speicher.einstellungen().get("import_ordner_zimmerpivot") or str(Path.home())
        pfad, _ = QFileDialog.getOpenFileName(self, "Zimmer-Pivot wählen", start, "Excel (*.xlsx *.xlsm);;Alle Dateien (*)")
        if not pfad:
            return
        speicher.einstellung_setzen("import_ordner_zimmerpivot", str(Path(pfad).parent))
        self.b_pivot.setEnabled(False)
        self.b_pivot.setText("Wird gelesen …")

        def fertig(ergebnis) -> None:
            zimmerpivot.speichern(ergebnis)
            self.z.meldung.emit(f"Zimmer-Pivot importiert: {ergebnis.zimmer} Zimmer, "
                                f"{ergebnis.zeitraum[0]:%d.%m.%Y} – {ergebnis.zeitraum[1]:%d.%m.%Y}.", "ok")
            self.neu_laden()

        self._pivot_worker = Worker(zimmerpivot.lesen, Path(pfad), parent=self)
        self._pivot_worker.fertig.connect(fertig)
        self._pivot_worker.fehler.connect(lambda t: self.z.meldung.emit(f"Zimmer-Pivot konnte nicht gelesen werden: {t}", "fehler"))
        self._pivot_worker.finished.connect(lambda: (self.b_pivot.setEnabled(True), self.b_pivot.setText("Zimmer-Pivot importieren")))
        self._pivot_worker.start()


# ======================================================================== Zimmer-Details

class ZimmerDialog(QDialog):
    """Wer wohnt wann im Zimmer – Liste und Zeitstrahl über drei Monate."""

    def __init__(self, stand: zp.Planstand, zid: str, parent=None):
        super().__init__(parent)
        z = stand.lage.zimmer[zid]
        self.setWindowTitle(z.id)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label(f"Zimmer {z.kurz}", "seitentitel"))
        heute = date.today()
        status, _ = stand.lage.status_am(z.id, heute)
        merkmale = QHBoxLayout()
        merkmale.setSpacing(6)
        merkmale.addWidget(Pille(STATUS_TEXT[status].capitalize() + " heute",
                                 {"frei": "ok", "teilweise": "knapp", "gesperrt": "ueber"}.get(status, "neutral")))
        merkmale.addWidget(label(f"{zp.flur_text(z)} · {z.betten} Bett{'en' if z.betten > 1 else ''}", "muted"))
        for text, an in (("Tiere erlaubt", z.tiere), ("nur Männer (Bad über den Flur)", z.nur_maenner),
                         ("Gästezimmer", z.gaeste)):
            if an:
                merkmale.addWidget(Pille(text, "akzent"))
        merkmale.addStretch()
        v.addLayout(merkmale)
        if status in ("frei", "teilweise"):
            bis = stand.lage.frei_bis(z.id, heute)
            v.addWidget(label(f"Frei bis {bis:%d.%m.%Y}" if bis else "Frei ohne Folgebelegung", "fett"))
        if z.notiz:
            v.addWidget(label(z.notiz, "klein", umbruch=True))
        from ... import inventar

        ausstattung = inventar.laden().kurztext(z.id)
        v.addWidget(label(f"<b>Ausstattung:</b> {ausstattung}" if ausstattung else
                          "Ausstattung: noch nichts erfasst (Seite „Inventar“)", "klein", umbruch=True))

        karte = Karte("Zeitstrahl", "letzte Woche bis in drei Monaten")
        zs = Zeitstrahl()
        zs.SPUR = 28
        von, bis = heute - timedelta(days=7), heute + timedelta(days=83)
        zs.setzen(zp.zeitstrahl(stand.lage, [z], von, bis), von, bis)
        karte.inhalt.addWidget(zs)
        v.addWidget(karte)

        liste = Karte("Belegungen", "")
        tab = Tabelle(["Von", "Bis", "Tage", "Wer / Was", "Art"], ["l", "l", "r", "l", "l"], dehnen=3)
        zeilen = []
        for b in sorted(stand.lage.belegungen.get(z.id, []), key=lambda b: b.von):
            if b.art == "freigabe":
                text, art = f"Zimmerfreigabe ({b.grund})", "Freigabe"
            else:
                text, art = zp.balken_text(b)
                art = {"belegt": "belegt", "geplant": "geplant (übernommen)", "pivot": "laut Zimmer-Pivot",
                       "gesperrt": "gesperrt"}[art]
            if b.bis < heute - timedelta(days=60):
                continue
            zeilen.append([f"{b.von:%d.%m.%Y}", f"{b.bis:%d.%m.%Y}", (b.bis - b.von).days + 1, text, art])
        tab.fuellen(zeilen)
        tab.hoehe_anpassen(10)
        liste.inhalt.addWidget(tab if zeilen else label("Keine Belegungen in den letzten 60 Tagen und danach.", "muted"))
        v.addWidget(liste)
        unten = QHBoxLayout()
        unten.addStretch()
        zu = knopf("Schließen", "primary")
        zu.clicked.connect(self.accept)
        unten.addWidget(zu)
        v.addLayout(unten)
        from ..dialoge import scrollbar_machen

        scrollbar_machen(self, 980, 680)
