"""Zimmerplan Goslar: Planen (Zuteilen, Zeitstrahl, Häuser), Erledigen (Aufgaben, Abreisen, Reinigung), Zimmer.

Importe (Gebäudeplan, ZKL, Zimmer-Pivot) stehen seit 6.14 unter Daten & Import, die Planungs-Einstellungen unter
Einstellungen, der Verlauf unter „Mehr“ (``belegung/ui/zimmerquellen.py``)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QHeaderView, QLineEdit, QMenu, QMessageBox, QSizePolicy, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ... import eintragen, gebaeudeplan, speicher, uwt, zimmerexport
from ... import zimmerplan as zp
from .. import drucken, icons, theme
from ..basis import Seite, Zustand, sichtbar
from ..widgets import FlowLayout, Hinweis, Karte, Leer, Pille, Segment, Tabelle, DatumFeld, knopf, label, leeren
from ..zeitstrahl import Zeitstrahl

GESCHLECHTER = [("", "?"), ("m", "m"), ("w", "w"), ("d", "d")]
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
          "November", "Dezember"]
HAEUSER = ["2", "3.1", "3.2", "3.3", "6"]
# Nach Aufgaben gruppiert: Planen | Erledigen (Tagesgeschäft) | Verwalten (Stammdaten, Importe, Protokoll)
TABS = ["Zuteilen", "Zeitstrahl", "Zimmer", "Aufgaben", "Abreisen", "Reinigung", "Stammdaten"]
ZS_ZEITRAEUME = {"wochen": "2 Wochen", "monat": "Monat", "quartal": "3 Monate"}
ZS_ARTEN = [("belegt", "belegt"), ("geplant", "geplant"), ("pivot", "Pivot"), ("gesperrt", "gesperrt")]
ZS_ARTEN_TIPP = {"belegt": "belegt laut Gebäudeplan bzw. fest (voll gefüllt)",
                 "geplant": "geplant im Zimmerplan (gestrichelter Rand)",
                 "pivot": "gebucht laut Zimmer-Pivot, im Gebäudeplan fehlend (gepunkteter Rand)",
                 "gesperrt": "gesperrt / Renovierung (schraffiert)"}
TAB_GRUPPEN = (3, 6)                         # Trennstrich vor „Aufgaben“ und vor „Stammdaten“
TAB_TIPPS = {
    "Zuteilen": "Planen: Anreisen Zimmer geben – Vorschlag prüfen, anpassen, übernehmen",
    "Zeitstrahl": "Planen: wer wann wo wohnt – ziehen = verschieben/Umzug, Rechtsklick = alle Aktionen",
    "Zimmer": "Zimmer finden: suchen und filtern (frei, renoviert, Vinyl, Tier …) – als Übersicht, Karten oder Liste",
    "Aufgaben": "Erledigen: im Belegungssystem eintragen, Konflikte, Engpässe",
    "Abreisen": "Erledigen: wer wann abreist – Liste drucken",
    "Reinigung": "Erledigen: Reinigungsliste der Woche",
    "Stammdaten": "Verwalten: Flur, Betten, Merkmale und Notiz je Zimmer",
}
WEGGEFALLEN = {"Quellen": "Zuteilen", "Häuser": "Zimmer"}   # „Zimmer“ (bis 6.14 Stammdaten + Liste) → Finder       # alte Reiter (gemerkte Tabs) → wohin stattdessen
TABS_VOR_610 = ["Zuteilen", "Aufgaben", "Zeitstrahl", "Häuser", "Reinigung", "Zimmer", "Quellen"]   # alte Nummern
ABREISE_ZEITRAUM = ["Heute", "Morgen", "Diese Woche", "Nächste Woche", "14 Tage", "Monat"]


def flur_text_lang(z: zp.Zimmer) -> str:
    return f"Zimmer {z.kurz} · {zp.flur_text(z)}"


class ZimmerplanSeite(Seite):
    titel = "Zimmerplan"
    untertitel = "Internat Goslar – Zimmer zuteilen und Belegung im Blick"
    zeigt_filter = False
    zeigt_bezug = False
    reiter_attr = "tabs"

    def __init__(self, zustand: Zustand, nebenfenster: bool = False):
        super().__init__(zustand)
        self.stand: zp.Planstand | None = None
        self._zuteilungen: list[zp.Zuteilung] = []
        self._fest: dict[str, str] = {}
        self._hand: set[str] = set()          # Zimmer in dieser Sitzung von Hand gewählt (Vorschau: „angefordert“)
        self._anreise_kennung: str | None = None
        self._anreise_liste: list = []
        self._monat = date.today().replace(day=1)
        zustand.listen_geaendert.connect(self.anstossen)   # auch ohne geladene Pivot aktualisieren
        zustand.zimmer_geaendert.connect(self._fremd_geaendert)   # anderes Fenster / Zimmerkarte hat gespeichert
        self._eigene_aenderung = False

        # Reiter + kompakte Kennzahlen (statt großer Kacheln – passt auch bei 125/150 % Skalierung)
        kopf = QHBoxLayout()
        kopf.setSpacing(10)
        self.tabs = Segment(TABS, 0, trenner=TAB_GRUPPEN, tipps=[TAB_TIPPS[t] for t in TABS])
        self.tabs.geaendert.connect(self._tab)
        kopf.addWidget(self.tabs, 0, Qt.AlignTop)
        kopf.addStretch()
        self.nebenfenster = nebenfenster
        self.kopf_aktion = None             # Hauptfenster legt die Knöpfe neben den Seitentitel
        if not nebenfenster:
            self.kopf_aktion = QWidget()
            ka = QHBoxLayout(self.kopf_aktion)
            ka.setContentsMargins(0, 0, 0, 0)
            ka.setSpacing(4)
            optimieren = knopf("Optimieren", "ghost", "funke", "Belegung prüfen: Regelverstöße, bessere Zimmer, Tausche")
            optimieren.clicked.connect(self.optimieren)
            mehr = knopf("Mehr", "ghost", None, "Verlauf der Änderungen, neues Fenster, Importe, Einstellungen")
            mehr.setMenu(self._mehr_menue())
            ka.addWidget(optimieren)
            ka.addWidget(mehr)
        self.anheften(kopf)                 # Reiter und Kennzahlen bleiben beim Scrollen oben stehen
        # Kennzahlen in eigener Zeile unter den Reitern – brechen bei schmalem Fenster sauber um
        kz = QWidget()
        kz.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)   # nicht in die Höhe wachsen
        self.kennzahlen = FlowLayout(kz, abstand=6)
        self.anheften(kz)
        self.hinweise = QVBoxLayout()
        self.hinweise.setSpacing(8)
        self.lay.addLayout(self.hinweise)

        self._woche = date.today()
        self._zs_arten: set[str] = set()      # Zeitstrahl-Filter nach Art (Legende anklicken)
        self._zs_maengel = False               # Zeitstrahl-Filter „!“: nur Zimmer mit offenen Mängeln
        bauen = {"Zuteilen": self._zuteilen_bauen, "Aufgaben": self._aufgaben_bauen, "Zeitstrahl": self._zeitstrahl_bauen,
                 "Zimmer": self._zimmer_bauen, "Reinigung": self._reinigung_bauen, "Abreisen": self._abreisen_bauen,
                 "Stammdaten": self._stamm_bauen}
        self.seiten = [bauen[t]() for t in TABS]
        for w in self.seiten:
            self.lay.addWidget(w)
        self.lay.addStretch()
        self._tab_anzeigen(0)

    # ------------------------------------------------------------------ ohne Pivot-Daten lauffähig

    def anstossen(self) -> None:
        self._veraltet = True
        if sichtbar(self):              # minimiert/im Infobereich: beim Zurückholen nachholen
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
        # Zeile 2: Zusammenfassung (bricht bei wenig Platz um), Zeile 3: Aktionen – „Übernehmen“ rechts
        status = QWidget()
        status.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.zu_status = FlowLayout(status, abstand=6)
        self.zu_karte.inhalt.addWidget(status)
        unter = QHBoxLayout()
        unter.setSpacing(8)
        self.b_excel = knopf("Drucken", "ghost", "drucker", "Anreiseliste, Zimmerschilder oder Schlüsselliste dieser Anreise "
                                                           "drucken – oder als Excel-Liste speichern")
        export = QMenu(self.b_excel)
        export.addAction("Anreiseliste drucken …", lambda: self._anreise_drucken("anreise"))
        export.addAction("Zimmerschilder drucken …", lambda: self._anreise_drucken("schilder"))
        export.addAction("Schlüsselliste drucken …", lambda: self._anreise_drucken("schluessel"))
        export.addSeparator()
        export.addAction("Als Excel-Liste speichern (Zimmer, Etagen, freie Zimmer) …", self._excel)
        self.b_excel.setMenu(export)
        self.b_ok = knopf("Übernehmen", "primary", "haken", "Zuteilung speichern – zählt dann bei weiteren Vorschlägen als belegt")
        self.b_ok.clicked.connect(self._uebernehmen)
        # Seltenes links unter „Mehr“ – rechts nebeneinander „Drucken“ und die Hauptaktion „Übernehmen“
        self.b_mehr = knopf("Mehr", "ghost", None, "Person hinzufügen, neu vorschlagen, Planung zurücknehmen")
        menue = QMenu(self.b_mehr)
        self.b_plus = menue.addAction("Person zu dieser Anreise hinzufügen …", self._person_hinzufuegen)
        menue.addAction("Neu vorschlagen (eigene Änderungen verwerfen)", self._neu_vorschlagen)
        menue.addSeparator()
        self.m_anreise = menue.addAction("Planung dieser Anreise zurücknehmen", self._anreise_zuruecknehmen)
        self.m_uwt_weg = menue.addAction("Alle kommenden UWT-Planungen zurücknehmen", self._uwt_zuruecknehmen)
        menue.addAction("Alle kommenden UWT neu automatisch zuteilen", self._uwt_neu)
        menue.aboutToShow.connect(self._zurueck_menue)
        self.b_mehr.setMenu(menue)
        aktionen = QWidget()            # Knöpfe brechen im schmalen Fenster um, statt die Seite zu verbreitern
        knoepfe = FlowLayout(aktionen, abstand=8)
        knoepfe.addWidget(self.b_mehr)
        unter.addWidget(aktionen, 1, Qt.AlignTop)
        unter.addWidget(self.b_excel, 0, Qt.AlignTop)
        unter.addWidget(self.b_ok, 0, Qt.AlignTop)
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
        """Zwei kompakte Zeilen über der Zeitleiste: (1) Zeitraum und Haus, (2) Suche, Filter, Legende.
        Gruppe, „wohnt/darf“ und Belegungsart stehen im Menü „Filter“ (mit Zähler und „Zurücksetzen“)."""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        e = speicher.einstellungen()
        self._zs_zeitraum = e.get("zs_zeitraum") if e.get("zs_zeitraum") in ZS_ZEITRAEUME else "monat"
        self._zs_start = date.today()
        self._zs_gruppen: set[str] = set()
        self._zs_modus = "wohnt"
        oben = QWidget()
        oben.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        fl = FlowLayout(oben, abstand=8)
        zurueck = knopf("", "icon", "links", "Zurück")
        zurueck.setAccessibleName("Zeitraum zurück")
        zurueck.clicked.connect(lambda: self._monat_wechseln(-1))
        vor = knopf("", "icon", "rechts", "Weiter")
        vor.setAccessibleName("Zeitraum weiter")
        vor.clicked.connect(lambda: self._monat_wechseln(1))
        heute = knopf("Heute", "ghost", None, "Zum heutigen Tag springen")
        heute.clicked.connect(lambda: self._monat_wechseln(0))
        self.monat_text = label("", "kartentitel")
        self.monat_text.setMinimumWidth(170)
        self.monat_text.setAlignment(Qt.AlignCenter)
        zeitraum = QWidget()
        zl = QHBoxLayout(zeitraum)
        zl.setContentsMargins(0, 0, 0, 0)
        zl.setSpacing(2)
        for x in (zurueck, self.monat_text, vor, heute):
            zl.addWidget(x)
        fl.addWidget(zeitraum)
        self.zs_zoom = Segment([ZS_ZEITRAEUME[k] for k in ZS_ZEITRAEUME], list(ZS_ZEITRAEUME).index(self._zs_zeitraum),
                               tipps=["Zwei Wochen – breite Tage, Namen gut lesbar", "Ein Kalendermonat",
                                      "Drei Monate – für lange Aufenthalte"])
        self.zs_zoom.geaendert.connect(self._zs_zoom_setzen)
        fl.addWidget(self.zs_zoom)
        self.zs_haus = Segment(["2", "3.1", "3.2", "3.3", "6", "Alle"], 0,
                               tipps=[f"Haus {h}" for h in HAEUSER] + ["Alle Häuser"])
        self.zs_haus.geaendert.connect(lambda _i: self._zeitstrahl_zeigen())
        haus = QWidget()
        hl = QHBoxLayout(haus)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        hl.addWidget(label("Haus", "klein"))
        hl.addWidget(self.zs_haus)
        fl.addWidget(haus)
        v.addWidget(oben)
        unten = QHBoxLayout()
        unten.setSpacing(8)
        self.zs_suche = QLineEdit()
        self.zs_suche.setPlaceholderText("Name oder Zimmer suchen …")
        self.zs_suche.setClearButtonEnabled(True)
        self.zs_suche.setAccessibleName("Zeitstrahl durchsuchen")

        self.zs_suche.addAction(icons.icon("suche", theme.T.text_3, 16), QLineEdit.LeadingPosition)
        self.zs_suche.setMinimumWidth(180)
        self.zs_suche.setMaximumWidth(280)
        self.zs_suche.textChanged.connect(lambda _t: self._zeitstrahl_zeigen())
        unten.addWidget(self.zs_suche, 1)
        self.zs_filter = knopf("Filter", "chip", "filter", "Gruppe, „wohnt dort / darf dort wohnen“ und Belegungsart")
        self.zs_filter_menue = QMenu(self.zs_filter)
        self.zs_filter_menue.aboutToShow.connect(self._zs_filter_menue)
        self.zs_filter.setMenu(self.zs_filter_menue)
        unten.addWidget(self.zs_filter)
        self.zs_reset = knopf("Zurücksetzen", "ghost", "schliessen", "Suche und alle Filter aufheben")
        self.zs_reset.clicked.connect(self._zs_zuruecksetzen)
        unten.addWidget(self.zs_reset)
        self.zs_aktiv = label("", "klein")
        unten.addWidget(self.zs_aktiv)
        unten.addStretch()
        leg = QWidget()
        self.zs_legende = QHBoxLayout(leg)
        self.zs_legende.setContentsMargins(0, 0, 0, 0)
        self.zs_legende.setSpacing(12)
        unten.addWidget(leg)
        self.zs_anzahl = label("", "klein")
        self.zs_anzahl.setToolTip("Zimmer oder Balken anklicken für Details")
        unten.addWidget(self.zs_anzahl)
        v.addLayout(unten)
        karte = Karte(abstand=8)
        self.zeitstrahl = Zeitstrahl()
        self.zeitstrahl.zimmer_geklickt.connect(self._zimmer_details)
        self.zeitstrahl.verschiebbar = True           # Balken in ein anderes Zimmer ziehen (Planung oder Umzug)
        self.zeitstrahl.gezogen.connect(self._zs_gezogen)
        self.zeitstrahl.kontext.connect(self._zs_menue)
        self.zeitstrahl.scrollbereich = self.scroll   # Datumszeile bleibt beim Scrollen oben stehen
        self.scroll.verticalScrollBar().valueChanged.connect(
            lambda _v: self.zeitstrahl.update() if self.zeitstrahl.isVisible() else None)
        karte.inhalt.addWidget(self.zeitstrahl)
        v.addWidget(karte)
        return w

    def _zs_filter_menue(self) -> None:
        m = self.zs_filter_menue
        m.clear()

        def schalter(menue, text, an, fn):
            a = menue.addAction(text, fn)
            a.setCheckable(True)
            a.setChecked(an)
            return a

        gr = m.addMenu("Gruppe")
        for g in zp.GRUPPEN:
            schalter(gr, zp.GRUPPE_LABEL.get(g, g), g in self._zs_gruppen,
                     lambda g=g: (self._zs_gruppen.symmetric_difference_update({g}), self._zeitstrahl_zeigen()))
        gr.addSeparator()
        for modus, text in (("wohnt", "… wohnt dort (andere blass)"), ("darf", "… darf dort wohnen (Regeln)")):
            schalter(gr, text, self._zs_modus == modus,
                     lambda md=modus: (setattr(self, "_zs_modus", md), self._zeitstrahl_zeigen()))
        schalter(m, "! nur Zimmer mit Mängeln", self._zs_maengel,
                 lambda: (setattr(self, "_zs_maengel", not self._zs_maengel), self._zeitstrahl_zeigen()))
        art = m.addMenu("Belegungsart")
        for a, text in ZS_ARTEN:
            schalter(art, f"nur Zimmer mit „{text}“", a in self._zs_arten,
                     lambda a=a: self._zs_art_umschalten(a, a not in self._zs_arten))

    def _zs_zuruecksetzen(self) -> None:
        self._zs_gruppen.clear()
        self._zs_arten.clear()
        self._zs_maengel = False
        self._zs_modus = "wohnt"
        self.zs_suche.blockSignals(True)
        self.zs_suche.clear()
        self.zs_suche.blockSignals(False)
        self._zeitstrahl_zeigen()

    def _zs_zoom_setzen(self, i: int) -> None:
        self._zs_zeitraum = list(ZS_ZEITRAEUME)[i]
        speicher.einstellung_setzen("zs_zeitraum", self._zs_zeitraum)
        self._zeitstrahl_zeigen()

    def _zs_bereich(self) -> tuple[date, date, str]:
        """(von, bis, Überschrift) für Zeitraum und Ankertag."""
        a = self._zs_start
        if self._zs_zeitraum == "wochen":
            von = a - timedelta(days=a.weekday())
            bis = von + timedelta(days=13)
            return von, bis, f"{von:%d.%m.} – {bis:%d.%m.%Y}"
        von = a.replace(day=1)
        monate = 3 if self._zs_zeitraum == "quartal" else 1
        m = von.month - 1 + monate
        bis = date(von.year + m // 12, m % 12 + 1, 1) - timedelta(days=1)
        if monate == 1:
            return von, bis, f"{MONATE[von.month - 1]} {von.year}"
        return von, bis, f"{MONATE[von.month - 1][:3]} – {MONATE[bis.month - 1][:3]} {bis.year}"

    def _abreisen_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        karte = Karte("Abreiseliste", "Wer wann aus welchem Zimmer auszieht – mit der nächsten Anreise ins Zimmer")
        oben = QWidget()
        fluss = FlowLayout(oben, abstand=12)
        self.ab_zeitraum = Segment(ABREISE_ZEITRAUM, 2)
        self.ab_zeitraum.geaendert.connect(lambda _i: self._abreise_zeitraum_setzen())
        fluss.addWidget(self.ab_zeitraum)
        datum = QWidget()
        dl = QHBoxLayout(datum)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(6)
        self.ab_von, self.ab_bis = DatumFeld(date.today()), DatumFeld(date.today())
        for text, feld in (("von", self.ab_von), ("bis", self.ab_bis)):
            dl.addWidget(label(text, "klein"))
            dl.addWidget(feld)
            feld.geaendert.connect(lambda _d: self._abreisen_zeigen())
        fluss.addWidget(datum)
        ausgabe = QWidget()
        al = QHBoxLayout(ausgabe)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(8)
        for text, variante, icon, fn in (("Drucken", "primary", "datei", lambda: self._abreisen_drucken(False)),
                                         ("PDF", "ghost", "datei", lambda: self._abreisen_drucken(True)),
                                         ("Kopieren", "ghost", "kopieren", self._abreisen_kopieren)):
            b = knopf(text, variante, icon)
            b.clicked.connect(fn)
            al.addWidget(b)
        fluss.addWidget(ausgabe)
        karte.inhalt.addWidget(oben)
        self.ab_info = label("", "muted", umbruch=True)
        karte.inhalt.addWidget(self.ab_info)
        self.ab_tab = Tabelle(["Abreise", "Zimmer", "Name", "Maßnahme", "Nächste Anreise"], ["l"] * 5, dehnen=2)
        self.ab_tab.setTextElideMode(Qt.ElideRight)
        self.ab_tab.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.ab_tab.setColumnWidth(3, 150)
        self.ab_tab.setToolTip("Doppelklick: Zimmer- und Personenkarte · Klick auf eine Überschrift: sortieren")
        self.ab_tab.cellDoubleClicked.connect(self._abreise_oeffnen)
        karte.inhalt.addWidget(self.ab_tab)
        v.addWidget(karte)
        self._abreisen: list = []
        self._abreise_zeitraum_setzen(still=True)
        return w

    def _abreise_zeitraum_setzen(self, still: bool = False) -> None:
        heute = date.today()
        i = self.ab_zeitraum.index()
        montag = heute - timedelta(days=heute.weekday())
        von, bis = {0: (heute, heute), 1: (heute + timedelta(days=1),) * 2,
                    2: (heute, montag + timedelta(days=6)), 3: (montag + timedelta(days=7), montag + timedelta(days=13)),
                    4: (heute, heute + timedelta(days=13)), 5: (heute, heute + timedelta(days=30))}[i]
        self.ab_von.setzen(von)
        self.ab_bis.setzen(bis)
        if not still:
            self._abreisen_zeigen()

    def _abreise_titel(self) -> str:
        von, bis = self.ab_von.datum(), self.ab_bis.datum()
        return f"{von:%d.%m.%Y}" if von == bis else f"{von:%d.%m.} – {bis:%d.%m.%Y}"

    def _abreisen_zeigen(self) -> None:
        from ... import cockpit

        if self.stand is None:
            return
        von, bis = self.ab_von.datum(), self.ab_bis.datum()
        if bis < von:
            von, bis = bis, von
        self._abreisen = cockpit.abreiseliste(self.stand, von, bis)
        wt = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        self.ab_tab.fuellen([[f"{a.tag:%d.%m.%Y} {wt[a.tag.weekday()]}", a.zimmer.removeprefix("GS-"),
                              a.name + (" (geplant)" if a.art == "geplant" else ""), a.massnahme,
                              f"{a.naechste:%d.%m.%Y}" if a.naechste else "–"] for a in self._abreisen])
        for r, a in enumerate(self._abreisen):
            if self.ab_tab.item(r, 3):
                self.ab_tab.item(r, 3).setToolTip(f"{a.massnahme}\nseit {a.anreise:%d.%m.%Y}" if a.anreise else a.massnahme)
        self.ab_tab.hoehe_anpassen(22)
        knapp = sum(1 for a in self._abreisen if a.naechste and (a.naechste - a.tag).days <= 1)
        self.ab_info.setText(f"<b>{len(self._abreisen)} Abreisen</b> {self._abreise_titel()}"
                             + (f" · <b>{knapp}</b> mit Anreise am selben oder nächsten Tag" if knapp else "")
                             + " · Umzüge zählen nicht als Abreise." if self._abreisen else
                             f"Keine Abreisen {self._abreise_titel()}.")

    def _abreise_oeffnen(self, r: int, _c: int = 0) -> None:
        from ..zimmerkarte import karte_oeffnen

        i = self.ab_tab.daten_zeile(r)
        if 0 <= i < len(self._abreisen):
            a = self._abreisen[i]
            karte_oeffnen(self, self.z, a.zimmer, a.schluessel)

    def _abreisen_drucken(self, pdf: bool) -> None:
        from ... import drucklisten

        von = self.ab_von.datum()
        self._html_ausgeben(drucklisten.abreiseliste_html(self._abreisen, self._abreise_titel()), False,
                            f"Abreiseliste_{von:%Y-%m-%d}.pdf" if pdf else None)

    def _abreisen_kopieren(self) -> None:
        from PySide6.QtGui import QGuiApplication

        QGuiApplication.clipboard().setText("\n".join(
            "\t".join([f"{a.tag:%d.%m.%Y}", a.zimmer.removeprefix("GS-"), a.name, a.massnahme,
                       f"{a.naechste:%d.%m.%Y}" if a.naechste else ""]) for a in self._abreisen))
        self.z.meldung.emit(f"{len(self._abreisen)} Abreisen kopiert – in Excel einfügen (Strg+V).", "ok")

    def _reinigung_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        zurueck = knopf("", "icon", "links", "Vorherige Woche")
        zurueck.clicked.connect(lambda: self._woche_wechseln(-1))
        vor = knopf("", "icon", "rechts", "Nächste Woche")
        vor.clicked.connect(lambda: self._woche_wechseln(1))
        heute = knopf("Diese Woche", "ghost")
        heute.clicked.connect(lambda: self._woche_wechseln(0))
        self.rg_titel = label("", "kartentitel")
        # Woche und Ausgabe-Knöpfe als zwei Gruppen, die im schmalen Fenster untereinander umbrechen
        oben = QWidget()
        fluss = FlowLayout(oben, abstand=12)
        woche = QWidget()
        leiste = QHBoxLayout(woche)
        leiste.setContentsMargins(0, 0, 0, 0)
        leiste.setSpacing(8)
        for x in (zurueck, self.rg_titel, vor, heute):
            leiste.addWidget(x)
        fluss.addWidget(woche)
        ausgabe = QWidget()
        aus_lay = QHBoxLayout(ausgabe)
        aus_lay.setContentsMargins(0, 0, 0, 0)
        aus_lay.setSpacing(8)
        for text, icon, fn in (("Drucken", "datei", self._reinigung_drucken), ("PDF", "datei", self._reinigung_pdf),
                               ("Excel", "tabelle", self._reinigung_excel)):
            b = knopf(text, "primary" if text == "Drucken" else "ghost", icon)
            b.clicked.connect(fn)
            aus_lay.addWidget(b)
        fluss.addWidget(ausgabe)
        v.addWidget(oben)
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

    def _zimmer_bauen(self) -> QWidget:
        from ..zimmerfinder import ZimmerFinder

        self.finder = ZimmerFinder(self)
        return self.finder

    def _stamm_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
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

    def _renovierungen_auto(self) -> None:
        from ... import zimmerliste as zl

        try:
            erg = zl.auto_import(self.stand)
        except Exception:                 # noqa: BLE001 – Import darf den Start nie verhindern
            return
        if erg is not None:
            n, fehler = erg
            self.stand = zp.laden()
            nicht = ", ".join("-".join(x.split()[:2]) for x in fehler[:5])
            self.z.neuigkeit.emit(f"Renovierungsliste übernommen: {n} Zimmer aktualisiert (Renovierung, Boden)"
                                  + (f" – nicht im Zimmerplan: {nicht}" if fehler else "") + ".", "ok", "zimmerplan:Zimmer", "")

    def _inventar_auto(self) -> None:
        from ... import inventar

        try:
            erg = inventar.auto_import({z.id for z in self.stand.zimmer})
        except Exception:                 # noqa: BLE001 – Import darf den Start nie verhindern
            return
        if erg is not None:
            n, je, fehler = erg
            was = " · ".join(f"{name}: {k} Zimmer" for name, k in je.items())
            self.z.neuigkeit.emit(f"Inventur übernommen ({was})" + (f" – {len(fehler)} Zeilen ohne Zimmer" if fehler else "")
                                  + ".", "ok", "inventar", "")

    def _zustand_auto(self) -> None:
        from ... import zimmerzustand

        try:
            erg = zimmerzustand.auto_import(self.stand)
        except Exception:                 # noqa: BLE001 – Import darf den Start nie verhindern
            return
        if erg is not None:
            self.stand = zp.laden()
            self.z.neuigkeit.emit(f"Zimmerzustand aus der ZKL übernommen: {erg.text()}.", "ok", "zimmerplan:Zimmer", "")

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
                              "Ab wie vielen Monaten: Einstellungen → Zimmerplanung.")
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

        from ... import eintragen

        ek = Karte("Engpässe – nächste 12 Wochen",
                   "Nach heutigem Stand (Gebäudeplan + Planungen). Anreisen ohne Liste fehlen noch – in Wirklichkeit "
                   "wird es eher enger.")
        b_grenzen = knopf("Grenzen …", "ghost", None, "Ab wann eine Woche als knapp bzw. kritisch gilt")
        b_grenzen.clicked.connect(self._engpass_grenzen)
        ek.aktion(b_grenzen)
        self.eng_def = label("", "klein", umbruch=True)
        self.eng_def.setTextFormat(Qt.RichText)
        ek.inhalt.addWidget(self.eng_def)
        self.eng_tab = Tabelle(["Woche", "Frei jetzt", "Frei nach Planung", "EMR", "Doppel UWT", "Lage (nach Planung)"],
                               ["l", "r", "r", "r", "r", "l"], dehnen=5)
        self.eng_tab.setToolTip("<br>".join(f"<b>{eintragen.ENGPASS_NAMEN[a]}:</b> {t}"
                                            for a, t in eintragen.ENGPASS_ERKLAERUNG.items()))
        ek.inhalt.addWidget(self.eng_tab)
        v.addWidget(ek)
        v.addStretch()
        return w

    # ================================================================== Anzeige

    def aktualisieren(self) -> None:
        self.neu_laden()

    def neu_laden(self) -> None:
        if self.nebenfenster:              # Importe und automatische UWT-Zuteilung nur im Hauptfenster
            self.stand = zp.laden()
            self._kopf_zeigen()
            self._aufgaben_zaehler()
            self._anreisen_fuellen()
            self._tab_inhalt(self.tabs.index())
            return
        neu = gebaeudeplan.automatisch_importieren()
        if neu is not None:
            belegt = sum(1 for b in neu.belegungen if b.art == "belegt")
            stand = f" (Stand {neu.stand:%d.%m.%Y})" if neu.stand else ""
            self.z.neuigkeit.emit(f"Gebäudeplan {neu.datei}{stand} automatisch übernommen: {belegt} Belegungen.", "ok",
                                  "daten:Gebäudeplan & ZKL", "")
        uwt_neu = uwt.automatisch_importieren()
        if uwt_neu:
            from ..hauptfenster import uwt_meldung

            self.z.neuigkeit.emit(uwt_meldung(uwt_neu), "ok", "daten:UWT", "")
        self.stand = zp.laden()
        self._renovierungen_auto()
        self._inventar_auto()
        self._zustand_auto()
        if neu is not None and (k := zp.konflikte(self.stand.lage)):
            self.z.neuigkeit.emit(f"Achtung: {len(k)} geplante Zimmer kollidieren mit dem neuen Gebäudeplan – "
                                "Hinweis im Zimmerplan, „Neu planen“ löst es.", "warnung", "zimmerplan:Aufgaben", "")
        # kommende UWT gleich zuteilen (DZ-Partner zusammen) – jede Person nur einmal automatisch
        try:
            auto = zp.uwt_automatisch_zuteilen(self.stand)
        except Exception:
            auto = []
        if auto:
            self.stand = zp.laden()
            klassen = sorted({zt.bedarf.massnahme.removeprefix("UWT ") for zt in auto})
            self.z.neuigkeit.emit(f"UWT automatisch zugeteilt: {len(auto)} Personen ({', '.join(klassen)}) – "
                                "unter Zuteilen änderbar.", "ok", "zimmerplan:Zuteilen", "")
        self._kopf_zeigen()
        self._aufgaben_zaehler()
        ziel = getattr(self.z, "zimmer_anreise", None)
        if ziel:
            # EMR sind schon am Vortag des Listendatums da – dann den Vortag wählen
            self._anreise_kennung = self._kennung_fuer_liste(ziel)
            self.z.zimmer_anreise = None
            self.tabs.setzen(0)
            self._tab_anzeigen(0)
        self._anreisen_fuellen()
        self._tab_inhalt(self.tabs.index())

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        scroll = getattr(self, "scroll", None)
        breite = scroll.viewport().width() if scroll is not None else self.width()
        self.tabs.eng_wenn_noetig(breite - 2 * 32)        # Seitenränder

    def _tab(self, i: int) -> None:
        self._tab_anzeigen(i)
        self._tab_inhalt(i)
        if self.nebenfenster and self.window() is not None:
            self.window().setWindowTitle(f"Zimmerplan – {TABS[i]}")

    def ansicht_lesen(self) -> dict:
        a = super().ansicht_lesen()
        a.update(zs_haus=self.zs_haus.index(), zs_suche=self.zs_suche.text(), monat=self._zs_start.isoformat(),
                 reiter_name=TABS[a["reiter"]] if 0 <= a.get("reiter", -1) < len(TABS) else "")
        return a

    def ansicht_setzen(self, ansicht: dict) -> None:
        """Tab gewechselt: Reiter, Haus, Suche und Monat des Zeitstrahls wie zuletzt in diesem Tab."""
        ansicht = dict(ansicht)
        if ansicht.get("reiter_name") in WEGGEFALLEN:   # z. B. „Quellen“ (bis 6.13)
            ansicht["reiter_name"] = WEGGEFALLEN[ansicht["reiter_name"]]
        if ansicht.get("reiter_name") in TABS:          # Reiter über den Namen – Nummern ändern sich mit neuen Reitern
            ansicht["reiter"] = TABS.index(ansicht["reiter_name"])
        elif isinstance(ansicht.get("reiter"), int) and 0 <= ansicht["reiter"] < len(TABS_VOR_610):
            alt = TABS_VOR_610[ansicht["reiter"]]                             # gespeichert vor 6.10 (nur Nummer)
            ansicht["reiter"] = TABS.index(WEGGEFALLEN.get(alt, alt))
        if isinstance(ansicht.get("zs_haus"), int):
            self.zs_haus.setzen(ansicht["zs_haus"])
        if isinstance(ansicht.get("zs_suche"), str):
            self.zs_suche.blockSignals(True)
            self.zs_suche.setText(ansicht["zs_suche"])
            self.zs_suche.blockSignals(False)
        try:
            self._zs_start = date.fromisoformat(ansicht["monat"])
            self._monat = self._zs_start.replace(day=1)
        except (KeyError, TypeError, ValueError):
            pass
        reiter = ansicht.get("reiter")
        if isinstance(reiter, int) and 0 <= reiter < len(TABS) and reiter != self.tabs.index():
            super().ansicht_setzen(ansicht)               # zeigt den Reiter (inkl. Inhalt)
        elif self.stand is not None:
            self._tab_inhalt(self.tabs.index())

    def _nach_aenderung(self) -> None:
        """Nach dem Speichern: andere Fenster und Zimmerkarten benachrichtigen, selbst neu laden."""
        self._eigene_aenderung = True
        try:
            self.z.zimmer_geaendert.emit()
        finally:
            self._eigene_aenderung = False
        self.neu_laden()

    def _fremd_geaendert(self) -> None:
        if not self._eigene_aenderung:
            self.anstossen()

    def _gebaeudeplan_importieren(self) -> None:
        from ..zimmerquellen import plan_importieren

        if plan_importieren(self, self.z):
            self.neu_laden()

    def _mehr_menue(self) -> QMenu:
        from ..zimmerquellen import verlauf_oeffnen

        m = QMenu(self)
        m.addAction(icons.icon("person", theme.T.text_2, 16), "Neuer Mieter – Unterlagen erstellen …", self.neuer_mieter)
        m.addAction("Mietvertrag verlängern (Nebenabrede) …", self.mieter_verlaengern)
        m.addSeparator()
        m.addAction("Verlauf – wer hat wann was geändert …", lambda: verlauf_oeffnen(self, self.z))
        m.addAction("Diesen Reiter in neuem Fenster öffnen", self._neues_fenster)
        m.addSeparator()
        m.addAction("Importe (Gebäudeplan, ZKL) …", lambda: self.z.navigieren.emit("daten:Gebäudeplan & ZKL"))
        m.addAction("Einstellungen der Zimmerplanung …", lambda: self.z.navigieren.emit("einstellungen"))
        return m

    def neuer_mieter(self, zimmer: str = "") -> None:
        from ..mieter_dialog import NeuerMieterDialog

        if NeuerMieterDialog(self.z, zimmer, self.window()).exec():
            self.neu_laden()

    def mieter_verlaengern(self, nr: str = "") -> None:
        from ..mieter_dialog import VerlaengernDialog

        if VerlaengernDialog(self.z, nr, self.window()).exec():
            self.neu_laden()

    def optimieren(self) -> None:
        from ..optimieren import OptimierenDialog

        OptimierenDialog(self.z, self.window()).exec()

    def _neues_fenster(self) -> None:
        from ..fenster import zimmerplan_fenster

        zimmerplan_fenster(self.z, self.tabs.index())

    def _tab_anzeigen(self, i: int) -> None:
        for k, w in enumerate(self.seiten):
            w.setVisible(k == i)

    def _tab_inhalt(self, i: int) -> None:
        if self.stand is None or not 0 <= i < len(TABS):
            return
        {"Aufgaben": self._aufgaben_zeigen, "Zeitstrahl": self._zeitstrahl_zeigen, "Zimmer": self.finder.zeigen,
         "Reinigung": self._reinigung_zeigen, "Abreisen": self._abreisen_zeigen, "Stammdaten": self._stamm_zeigen}.get(TABS[i], lambda: None)()

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
        try:
            self._nach_planung = eintragen.nach_planung(st, heute, 12)
        except Exception:                 # noqa: BLE001 – Anzeige darf nie den Zimmerplan blockieren
            self._nach_planung = None
        leeren(self.kennzahlen)
        for text, stufe, tip in ((f"{zaehler['frei']} frei", "ok", "Freie Zimmer heute (inkl. teilweise freier Doppelzimmer)"),
                                 (f"{zaehler['belegt']} belegt", "neutral", "Belegte Zimmer heute"),
                                 (f"{zaehler['gesperrt']} gesperrt", "neutral", "Gesperrt oder in Renovierung"),
                                 (f"{offen} ohne Zimmer", "knapp" if offen else "ok", "Anreisen der nächsten 8 Wochen ohne übernommenes Zimmer")):
            p = Pille(text, stufe)
            p.setToolTip(tip)
            self.kennzahlen.addWidget(p)
        np_ = self._nach_planung
        if np_ is not None and (w := np_.tiefst) is not None:
            p = Pille(f"nach Planung mind. {w.gesamt} frei · {w.text.split(' · ')[0]}",
                      {"ok": "ok", "knapp": "knapp", "kritisch": "ueber"}[w.stufe("gesamt")])
            p.setToolTip("Wenn alle Anreisen der nächsten 12 Wochen ein Zimmer haben (auch die "
                         f"{np_.offen} noch ohne Zimmer – probeweise nach den Regeln zugeteilt"
                         + (f", {np_.ohne_platz} fänden keins" if np_.ohne_platz else "") + "):<br>"
                         + "<br>".join(f"{n.text}: <b>{n.gesamt}</b> frei (jetzt {j.gesamt})" for j, n in np_.wochen))
            self.kennzahlen.addWidget(p)
        from ... import maengel as mg

        aktiv = {z.id for z in st.zimmer if z.aktiv}
        je_zimmer = {zid: ms for zid, ms in mg.offen_je_zimmer().items() if zid in aktiv}
        if je_zimmer:                                # „!“ – ein Klick zeigt genau diese Zimmer (und den FM-Bericht)
            from ..widgets import mangel_farben, mangel_icon, mangel_marke

            stufen = [mg.stufe(ms) for ms in je_zimmer.values()]
            hoechste = max(stufen)
            b = knopf(f"{len(je_zimmer)} Zimmer mit Mängeln", "chip", None,
                      "Zimmer mit offenen Mängeln zeigen – Bericht für das FM dort unter „Drucken“<br>"
                      + "<br>".join(f"{mg.stufe_text(s)}: {stufen.count(s)} Zimmer" for s in (3, 2, 1))
                      + ("<br>Nicht bewohnbar (werden nicht zugeteilt): "
                         + ", ".join(sorted(st.lage.zimmer[z].kurz for z, ms in je_zimmer.items() if mg.stufe(ms) == 3))
                         if hoechste == 3 else ""))
            farbe = mangel_farben(hoechste)[0]
            b.setStyleSheet(f"font-weight: 700; border: 2px solid {farbe};")
            b.setIcon(mangel_icon(hoechste, 16))
            b.clicked.connect(self.maengel_zeigen)
            self.kennzahlen.addWidget(b)
            for s_ in (3, 2, 1):                     # je Signalfarbe eine Zahl: rot · orange · gelb
                if (n := stufen.count(s_)):
                    zahl = mangel_marke(s_, f"{mg.stufe_text(s_)}: {n} Zimmer")
                    zahl.setText(str(n))
                    self.kennzahlen.addWidget(zahl)
        leeren(self.hinweise)
        if st.plan is None:
            h = Hinweis("Noch kein Gebäudeplan da – die Zimmer sind bekannt, die aktuelle Belegung aber nicht. "
                        "Plan importieren oder in den Ordner „Gebaeudeplan“ legen.",
                        "warnung", "Gebäudeplan importieren")
            h.knopf.clicked.connect(self._gebaeudeplan_importieren)
            self.hinweise.addWidget(h)
        elif st.plan.stand and (heute - st.plan.stand).days > 7:
            h = Hinweis(f"Der Gebäudeplan ist vom {st.plan.stand:%d.%m.%Y} – für verlässliche Vorschläge bitte den "
                        "aktuellen Plan importieren.", "info", "Importieren")
            h.knopf.clicked.connect(self._gebaeudeplan_importieren)
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
                        f"{'Zimmer ist' if len(k) == 1 else 'Zimmer sind'} inzwischen belegt, gesperrt oder nicht mehr zulässig:</b><br>"
                        + "<br>".join(zeilen), "fehler", "Neu planen")
            h.setToolTip("<br>".join(x.text for x in k))
            h.knopf.setToolTip("Für diese Personen (und ihre DZ-Partner) ein freies Zimmer suchen und speichern")
            h.knopf.clicked.connect(self._konflikte_loesen)
            self.hinweise.addWidget(h)
        dz_hinweise = [h for h in (uwt.klassen_info().get("hinweise") or []) if "noch keine DZ-Liste" not in h]
        if dz_hinweise:
            self.hinweise.addWidget(Hinweis("<b>UWT-Klassenübersicht:</b> " + " ".join(dz_hinweise), "info"))
        anders = [a for a in st.lage.abgleich if a.art == "anders"]
        # „fehlt“ nur, wenn der Gebäudeplan nach der Anreise erstellt wurde (sonst kann die Person gar nicht
        # drinstehen) und die Buchung unter Aufgaben noch nicht als eingetragen abgehakt ist
        haken = eintragen._haken()
        fehlt = [a for a in st.lage.abgleich if a.art == "fehlt"
                 and f"{a.person}|{a.geplant}|{a.von.isoformat()}" not in haken
                 and (st.plan.stand is None or st.plan.stand >= a.von)]
        for liste, titel, art in ((anders, "Im Gebäudeplan anders gebucht als geplant", "info"),
                                  (fehlt, "Angereist? Im Gebäudeplan noch nicht gebucht", "warnung")):
            if not liste:
                continue
            zeilen = [a.text for a in liste[:6]] + ([f"… und {len(liste) - 6} weitere"] if len(liste) > 6 else [])
            if liste is fehlt:
                zeilen.append("<i>Schon im Belegungssystem eingetragen? Unter „Aufgaben“ abhaken – dann verschwindet "
                              "der Hinweis; mit dem nächsten Gebäudeplan wird ohnehin neu abgeglichen.</i>")
            h = Hinweis(f"<b>{titel} ({len(liste)}):</b><br>" + "<br>".join(zeilen), art,
                        "Zu Aufgaben" if liste is fehlt else None)
            if liste is fehlt:
                h.knopf.clicked.connect(lambda: (self.tabs.setzen(TABS.index("Aufgaben")), self._tab(TABS.index("Aufgaben"))))
            h.setToolTip("<br>".join(a.text for a in liste))
            self.hinweise.addWidget(h)
        self._hinweise_falten()

    def maengel_zeigen(self) -> None:
        """Reiter „Zimmer“ mit Filter „!“ (nur Zimmer mit offenen Mängeln, alle Häuser)."""
        i = TABS.index("Zimmer")
        self.tabs.setzen(i)
        self._tab(i)
        self.finder.nur_maengel()

    def _hinweise_falten(self) -> None:
        """Info-Hinweise hinter einen Knopf in der Kennzahlen-Zeile – Warnungen und Konflikte bleiben sichtbar.
        So bleibt auf jedem Reiter Platz für den eigentlichen Inhalt."""
        alle = [self.hinweise.itemAt(i).widget() for i in range(self.hinweise.count())]
        infos = [h for h in alle if isinstance(h, Hinweis) and h.property("hinweis") == "info"]
        if not infos:
            return
        offen = bool(speicher.einstellungen().get("zp_hinweise_offen", False))
        b = knopf(f"{len(infos)} Hinweis{'e' if len(infos) > 1 else ''}", "chip", "info")
        b.setCheckable(True)
        b.setChecked(offen)
        texte = [h.findChildren(QLabel)[1].text() for h in infos if len(h.findChildren(QLabel)) > 1]
        b.setToolTip("Ein- oder ausblenden:<br>• " + "<br>• ".join(t.split("<br>")[0][:120] for t in texte))

        def umschalten(an: bool) -> None:
            for h in infos:
                h.setVisible(an)
            speicher.einstellung_setzen("zp_hinweise_offen", an)

        b.toggled.connect(umschalten)
        for h in infos:
            h.setVisible(offen)
        self.kennzahlen.addWidget(b)

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
        self._hand = set()
        self._berechnen()

    def _neu_vorschlagen(self) -> None:
        self._fest, self._hand = {}, set()
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
        self._hand.add(b.schluessel)
        if zid:
            self._fest[b.schluessel] = zid
        else:
            self._fest.pop(b.schluessel, None)
        self._berechnen()

    def _uebernehmen(self) -> None:
        """Vorher zeigen, was sich gegenüber dem *jetzt* Gespeicherten ändert (auch für andere Personen dieser
        Anreise); Konflikte (inzwischen belegt, woanders geändert) blockieren. Nur neue Planungen: ohne Dialog."""
        from ... import aenderungen
        from ..aenderung_ui import ausfuehren, bestaetigen

        zts = list(self._zuteilungen)
        ohne = {z.bedarf.schluessel for z in zts if z.zimmer is None}
        v = aenderungen.zuweisungen_vorschau(zp.laden(), zts, ohne, self._hand, gesehen=self.stand.zuweisungen)
        if v.leer:
            self.z.meldung.emit("Nichts zu übernehmen – diese Zuteilung ist schon so gespeichert.", "info")
            return
        tag = zts[0].bedarf.von if zts else date.today()
        if not bestaetigen(self, v, "Zuteilung übernehmen", "Übernehmen", f"Anreise am {tag:%d.%m.%Y}: Das wird "
                           "gegenüber dem gespeicherten Stand geändert. Grau: was dadurch zusätzlich passiert."):
            return
        neu, um, weg = len(v.nach_art("neu")), len(v.nach_art("umgeplant")), len(v.nach_art("entfernt"))
        teile = [f"{neu} neu geplant"] * bool(neu) + [f"{um} umgeplant"] * bool(um) + [f"{weg} Planung entfernt"] * bool(weg)
        rest = len(ohne) - weg

        def speichern():
            zp.zuweisungen_speichern(zts)
            zp.zuweisungen_entfernen(ohne)

        if ausfuehren(self, self.z, f"Zuteilung Anreise {tag:%d.%m.}", speichern,
                      f"Anreise {tag:%d.%m.}: " + ", ".join(teile) + (f"; {rest} weiterhin ohne Zimmer." if rest > 0 else "."),
                      "warnung" if ohne else "ok"):
            self._hand = set()
            self._nach_aenderung()

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

        np_ = getattr(self, "_nach_planung", None) or eintragen.nach_planung(self.stand)
        self.eng_def.setText("<br>".join(f"<b>{eintragen.ENGPASS_NAMEN[a]}</b> = {t}"
                                         for a, t in eintragen.ENGPASS_ERKLAERUNG.items())
                             + f"<br><b>Ampel:</b> {eintragen.grenzen_text()}."
                             + f"<br><b>Nach Planung</b> = wenn auch die {np_.offen} Anreisen ohne Zimmer probeweise "
                               "nach den Regeln zugeteilt sind (nichts wird gespeichert); EMR, Doppel und Lage gelten "
                               "nach Planung." + (f" <b>{np_.ohne_platz} fänden kein Zimmer.</b>" if np_.ohne_platz else ""))
        t = theme.T
        farbe = {"ok": t.ok, "knapp": t.knapp, "kritisch": t.ueber}
        zeilen, farben = [], {}
        for r, (j, w) in enumerate(np_.wochen):
            stufe = w.gesamtstufe
            text = {"ok": "ok", "knapp": "knapp", "kritisch": "kritisch"}[stufe]
            if stufe != "ok":
                engpass = [n for a, n in (("gesamt", "Zimmer"), ("emr", "EMR"), ("doppel", "Doppelzimmer"))
                           if w.stufe(a) != "ok"]
                text += " – " + ", ".join(engpass)
            zeilen.append([w.text, j.gesamt, w.gesamt, w.emr, w.doppel, text])
            for c, art in ((2, "gesamt"), (3, "emr"), (4, "doppel")):
                if w.stufe(art) != "ok":
                    farben[(r, c)] = farbe[w.stufe(art)]
            farben[(r, 5)] = farbe[stufe]
        self.eng_tab.fuellen(zeilen, farben)
        self.eng_tab.hoehe_anpassen(len(zeilen))

    def _engpass_grenzen(self) -> None:
        from ... import eintragen
        from ..dialoge import EngpassGrenzenDialog

        if EngpassGrenzenDialog(self).exec():
            self.z.meldung.emit("Engpass-Grenzen gespeichert: " + eintragen.grenzen_text() + ".", "ok")
            self._engpaesse_zeigen()
            self.z.zimmer_geaendert.emit()

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

    # ---- Zeitstrahl: Ziehen und Rechtsklick ---------------------------------------------------

    def _zs_gezogen(self, b, nach: str, tag) -> None:
        """Geplant und noch nicht angereist: ganze Planung verschieben. Sonst: Umzug ab dem Tag des Loslassens."""
        from ..zeitstrahl import ganz_verschieben

        if ganz_verschieben(b):
            self._zs_verschieben(b.person, b.zimmer, nach)
            return
        self._umzug(b, nach=nach, ab=tag if tag and tag >= date.today() else None)

    def _umzug(self, b, nach: str | None = None, ab=None) -> None:
        from ..umzug_dialog import umzug_oeffnen

        if b.umzug and b.umzug in self.stand.lage.umzuege:
            u = self.stand.lage.umzuege[b.umzug]
            if nach == u.von_zimmer:
                nach = None
            umzug_oeffnen(self, self.z, uid=b.umzug, nach=nach, ab=None)
        else:
            from ... import umzug as um

            umzug_oeffnen(self, self.z, zid=b.zimmer, schluessel=um.schluessel_zu(self.stand, b), name=b.name,
                          nach=nach, ab=ab)

    def _status_person(self, person: str, belegt: bool, name: str) -> None:
        from ..aenderung_ui import ausfuehren

        text = f"{name}: {'Planung abgeschlossen (fest)' if belegt else 'wieder geplant'}"
        if ausfuehren(self, self.z, text, lambda: zp.status_setzen(person, belegt, "Zeitstrahl"), text + "."):
            self._nach_aenderung()

    def _status_umzug(self, uid: str, belegt: bool) -> None:
        from ... import umzug as um

        from ..aenderung_ui import ausfuehren

        u = self.stand.lage.umzuege.get(uid) if self.stand else None
        text = f"{u.name if u else 'Umzug'}: Umzug {'abgeschlossen (fest)' if belegt else 'wieder geplant'}"
        if ausfuehren(self, self.z, text, lambda: um.status_setzen(uid, belegt, "Zeitstrahl"), text + "."):
            self._nach_aenderung()

    def _zs_menue(self, obj, pos) -> None:
        from ..umzug_dialog import zurueck_nehmen
        from ..zeitstrahl import ganz_verschieben, ziehbar_balken
        from ..zimmerkarte import karte_oeffnen

        if self.stand is None:
            return
        m = QMenu(self)
        if isinstance(obj, tuple) and ziehbar_balken(obj[1].belegung):
            zid, b = obj[0], obj[1].belegung
            titel = m.addAction(f"{b.name} · {b.von:%d.%m.} – {b.bis:%d.%m.%Y}")
            titel.setEnabled(False)
            m.addSeparator()
            schluessel = zp.bewohner_aus(self.stand, b).schluessel
            m.addAction("Person öffnen (Zimmer, Abreise, Notizen) …",
                        lambda: karte_oeffnen(self, self.z, zid, schluessel))
            if b.umzug and b.umzug in self.stand.lage.umzuege:
                u = self.stand.lage.umzuege[b.umzug]
                m.addAction(f"Umzug ändern ({u.von_zimmer.removeprefix('GS-')} → "
                            f"{u.nach_zimmer.removeprefix('GS-')} ab {u.ab:%d.%m.}) …", lambda: self._umzug(b))
                if u.status in ("aktiv", "konflikt"):
                    m.addAction("Umzug wieder auf geplant" if u.belegt else "Umzug abschließen (fest)",
                                lambda: self._status_umzug(u.id, not u.belegt))
                m.addAction("Umzug zurücknehmen", lambda: zurueck_nehmen(self, self.z, b.umzug))
            elif ganz_verschieben(b):              # noch nicht eingezogen: Zimmer in der Personenkarte wählen
                m.addAction("Zimmer wechseln …", lambda: karte_oeffnen(self, self.z, zid, schluessel))
            elif b.bis >= date.today():            # eingezogen: Umzug ab einem Tag
                m.addAction("Zimmer wechseln (Umzug ab …) …", lambda: self._umzug(b))
            if not b.umzug and b.person and self.stand.zugewiesen(b.person):
                m.addAction("Wieder auf geplant" if b.art == "belegt" else "Planung abschließen (fest)",
                            lambda: self._status_person(b.person, b.art != "belegt", b.name))
        else:
            zid = obj[0] if isinstance(obj, tuple) else obj
            m.addAction(f"Zimmer {zid.removeprefix('GS-')} öffnen …", lambda: karte_oeffnen(self, self.z, zid))
        m.exec(pos)

    # ---- Zeitstrahl: geplante Zuweisung per Ziehen verschieben ------------------------------

    def _zs_verschieben(self, person: str, von: str, nach: str) -> None:
        from ..aenderung_ui import zimmer_wechseln_geplant

        if self.stand is not None and zimmer_wechseln_geplant(self, self.z, self.stand, person, nach, "Zeitstrahl verschoben"):
            self._nach_aenderung()
        elif self.stand is not None:
            self.neu_laden()                   # z. B. inzwischen woanders geändert: frisch anzeigen

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
        from ..aenderung_ui import ausfuehren

        if ausfuehren(self, self.z, f"Planung zurückgenommen ({len(geplant)} Personen)",
                      lambda: zp.planung_zuruecknehmen(geplant), lambda n: f"Planung zurückgenommen: {n} Personen ohne Zimmer."):
            self._nach_aenderung()

    def _uwt_zuruecknehmen(self) -> None:
        personen = self._kommende_uwt()
        if not personen or QMessageBox.question(
                self, "UWT-Planungen zurücknehmen", f"Die Zimmer aller kommenden UWT ({len(personen)} Personen) "
                "entfernen? Sie werden danach nicht wieder automatisch zugeteilt – über „Alle kommenden UWT neu "
                "automatisch zuteilen“ geht das jederzeit wieder.") != QMessageBox.Yes:
            return
        from ..aenderung_ui import ausfuehren

        if ausfuehren(self, self.z, "UWT-Planungen zurückgenommen", lambda: zp.planung_zuruecknehmen(personen),
                      lambda n: f"UWT-Planungen zurückgenommen: {n} Personen."):
            self._nach_aenderung()

    def _uwt_neu(self) -> None:
        if QMessageBox.question(
                self, "UWT neu zuteilen", "Alle kommenden UWT-Planungen verwerfen (auch Änderungen von Hand) und neu "
                "automatisch zuteilen – DZ-Paare zusammen?") != QMessageBox.Yes:
            return
        from ..aenderung_ui import ausfuehren

        if ausfuehren(self, self.z, "UWT neu zugeteilt", lambda: zp.uwt_neu_zuteilen(self.stand),
                      lambda neu: f"UWT neu zugeteilt: {len(neu)} Personen."):
            self._nach_aenderung()

    def _konflikte_loesen(self) -> None:
        personen = {k.person for k in getattr(self, "_konflikte", [])}
        if not personen:
            return
        from ... import aenderungen
        from ..aenderung_ui import VorschauDialog, ausfuehren

        frisch = zp.laden()
        verwaist, erg = zp.neu_planen_vorschlag(frisch, personen)
        ohne = [zt.bedarf for zt in erg if zt.zimmer is None]
        v = aenderungen.zuweisungen_vorschau(frisch, [zt for zt in erg if zt.zimmer], set(verwaist) | {b.schluessel for b in ohne},
                                             personen)
        if VorschauDialog(v, "Konflikte lösen", "Neu planen", "Die betroffenen Personen bekommen ein freies Zimmer. "
                          "„Vorschlag“: DZ-Partner, die mitziehen, damit das Paar zusammenbleibt. Wer kein Zimmer findet, "
                          "verliert die Planung und steht unter Zuteilen.", self).exec() != QDialog.Accepted:
            return

        def meldung(ergebnis) -> str:
            neu, ohne = ergebnis
            text = f"Neu geplant: {len(neu)} Personen in freien Zimmern."
            if ohne:
                text += f" Kein freies Zimmer für {', '.join(b.name for b in ohne[:4])}" + (" …" if len(ohne) > 4 else "") + \
                        " – bitte unter Zuteilen von Hand festlegen."
            return text

        if ausfuehren(self, self.z, "Konflikte neu geplant", lambda: zp.neu_planen_speichern(verwaist, erg), meldung,
                      "warnung" if ohne else "ok"):
            self._nach_aenderung()

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
        """Zurück/weiter um den angezeigten Zeitraum (2 Wochen bzw. einen Monat); 0 = heute."""
        if schritt == 0:
            self._zs_start = date.today()
        elif self._zs_zeitraum == "wochen":
            self._zs_start += timedelta(days=14 * schritt)
        else:
            a = self._zs_start.replace(day=1)
            m = a.month - 1 + schritt
            self._zs_start = date(a.year + m // 12, m % 12 + 1, 1)
        self._monat = self._zs_start.replace(day=1)
        self._zeitstrahl_zeigen()

    def _zeitstrahl_zeigen(self) -> None:
        if self.stand is None:
            return
        von, bis, titel = self._zs_bereich()
        self.monat_text.setText(titel)
        i = self.zs_haus.index()
        suche = self.zs_suche.text().strip().lower()
        # Suche gilt für alle Häuser – ein Zimmer oder eine Person findet man, ohne erst das Haus zu wählen
        zimmer = [z for z in self.stand.zimmer if z.aktiv and (i == 5 or bool(suche) or z.haus == HAEUSER[i])]
        gruppen, modus = set(self._zs_gruppen), self._zs_modus
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
        from ... import maengel as mg

        stufen = {zid: mg.stufe(ms) for zid, ms in mg.offen_je_zimmer().items()}
        self.zeitstrahl.maengel = stufen             # „!“ in Signalfarbe an der Zimmernummer
        if self._zs_maengel:
            zeilen = [(z, spuren) for z, spuren in zeilen if z.id in stufen]
        if suche:
            zeilen = [(z, spuren) for z, spuren in zeilen
                      if suche in z.id.lower() or suche in z.nr.lower() or suche in z.kurz.lower()
                      or any(suche in bk.text.lower() for spur in spuren for bk in spur)]
        self.zeitstrahl.setzen(zeilen, von, bis)
        if suche and i != 5:
            self.zs_haus.setToolTip("Bei einer Suche werden alle Häuser durchsucht")
        # aktive Filter benennen (nicht nur ein Punkt): was wirkt gerade auf die Zeilen?
        aktiv = ([f"Gruppe: {', '.join(zp.GRUPPE_LABEL.get(g, g) for g in zp.GRUPPEN if g in gruppen)}"
                  + (" (darf)" if modus == "darf" else "")] if gruppen else []) + \
                ([f"nur {', '.join(t for a, t in ZS_ARTEN if a in self._zs_arten)}"] if self._zs_arten else []) + \
                (["! nur Zimmer mit Mängeln"] if self._zs_maengel else [])
        n = len(aktiv) + bool(suche)
        self.zs_filter.setText(f"Filter {len(aktiv)}" if aktiv else "Filter")
        self.zs_filter.setProperty("aktiv", "true" if aktiv else "false")
        self.zs_filter.style().unpolish(self.zs_filter)
        self.zs_filter.style().polish(self.zs_filter)
        self.zs_reset.setVisible(n > 0)
        self.zs_aktiv.setText(" · ".join(aktiv))
        self.zs_aktiv.setVisible(bool(aktiv))
        from ..zeitstrahl import muster

        leeren(self.zs_legende)              # kleine Legende: Muster + Wort (Form und Farbe, nicht nur Farbe)
        for art, text in ZS_ARTEN:
            eintrag = QLabel()
            eintrag.setPixmap(muster(art, 20, 11))
            eintrag.setToolTip(ZS_ARTEN_TIPP[art])
            self.zs_legende.addWidget(eintrag)
            t = label(text, "klein")
            t.setToolTip(ZS_ARTEN_TIPP[art])
            self.zs_legende.addWidget(t)
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

    def _zimmer_details(self, zid: str) -> None:
        """Zimmer- und Personenkarte (eigenes Fenster, mehrere gleichzeitig möglich)."""
        from ..zimmerkarte import karte_oeffnen

        if self.stand and zid in self.stand.lage.zimmer:
            karte_oeffnen(self, self.z, zid)

    def anreise_zeigen(self, tag: date) -> None:
        """Reiter „Zuteilen“ mit der Anreise dieses Tages (z. B. aus der Startseite)."""
        self._anreise_kennung = tag.isoformat()
        i = TABS.index("Zuteilen")
        self.tabs.setzen(i)
        self._tab_anzeigen(i)
        if self.stand is not None:
            self._anreisen_fuellen()
            self._tab_inhalt(i)

    def zimmer_im_zeitstrahl(self, zid: str) -> None:
        """Zeitstrahl mit dem Haus des Zimmers und dem Zimmer im Suchfeld zeigen."""
        if self.stand is None or zid not in self.stand.lage.zimmer:
            return
        z = self.stand.lage.zimmer[zid]
        self.zs_haus.setzen(HAEUSER.index(z.haus) if z.haus in HAEUSER else 5)
        self.zs_suche.setText(z.id)
        i = TABS.index("Zeitstrahl")
        self.tabs.setzen(i)
        self._tab(i)

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
        self._nach_aenderung()

    # ================================================================== Ende
