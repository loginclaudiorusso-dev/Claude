"""Mieter: alle Mietverträge auf einen Blick – Ablauf, Verlängerung (Nebenabrede), Unterlagen neu erstellen –
dazu die Mieter laut Gebäudeplan, die (noch) nicht mit dem Programm angelegt wurden."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QSizePolicy, QWidget

from ... import mieter as mt
from ... import zimmerplan as zp
from ..basis import Seite, Zustand, sichtbar
from ..widgets import Karte, Leer, Pille, Tabelle, knopf, leeren


class MieterSeite(Seite):
    titel = "Mieter"
    untertitel = "Mietverträge, Verlängerungen und Unterlagen"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self._vertraege: list[mt.Mietvertrag] = []
        self._weitere: list = []

        kopf = QWidget()
        h = QHBoxLayout(kopf)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        self.kennzahlen = QWidget()
        self.kz = QHBoxLayout(self.kennzahlen)        # eine Zeile – FlowLayout würde den angehefteten Kopf aufblähen
        self.kz.setContentsMargins(0, 0, 0, 0)
        self.kz.setSpacing(6)
        h.addWidget(self.kennzahlen, 1, Qt.AlignVCenter)
        neu = knopf("Neuer Mieter", "primary", "plus", "Name, Zimmer, ab wann – erstellt alle Unterlagen als eine PDF "
                                                        "und trägt den Mieter im Zimmerplan ein")
        neu.clicked.connect(self._neu)
        h.addWidget(neu, 0, Qt.AlignVCenter)
        self.anheften(kopf)

        self.hinweis = Leer("person", "Noch keine Mietverträge mit dem Programm erstellt",
                            "„Neuer Mieter“ erstellt Mietvertrag, Wohnungsgeberbestätigung, SEPA-Mandat und "
                            "Mietschuldenfreiheitsbescheinigung in einer PDF.")
        self.lay.addWidget(self.hinweis)

        self.k_vertraege = Karte("Mietverträge", "Doppelklick öffnet die Personenkarte · „endet bald“ = in den nächsten "
                                                f"{mt.BALD_TAGE // 7} Wochen")
        self.tab = Tabelle(["Nr.", "Name", "Zimmer", "Beginn", "Ende", "Miete", "Status", "Verlängert"],
                           ["l", "l", "l", "l", "l", "r", "l", "l"], dehnen=1)
        self.tab.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tab.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tab.cellDoubleClicked.connect(lambda r, _c: self._oeffnen(r))
        self.tab.itemSelectionChanged.connect(self._auswahl)
        self.k_vertraege.inhalt.addWidget(self.tab)
        aktionen = QHBoxLayout()
        aktionen.setSpacing(8)
        self.b_verl = knopf("Verlängern (Nebenabrede) …", "ghost", "kalender")
        self.b_verl.clicked.connect(self._verlaengern)
        self.b_neu_pdf = knopf("Unterlagen neu erstellen …", "ghost", "drucker")
        self.b_neu_pdf.clicked.connect(self._unterlagen)
        self.b_karte = knopf("Personenkarte", "ghost", "person")
        self.b_karte.clicked.connect(lambda: self._oeffnen(self.tab.currentRow()))
        for b in (self.b_verl, self.b_neu_pdf, self.b_karte):
            aktionen.addWidget(b)
        aktionen.addStretch()
        self.k_vertraege.inhalt.addLayout(aktionen)
        self.lay.addWidget(self.k_vertraege)

        self.k_weitere = Karte("Weitere Mieter laut Gebäudeplan",
                               "Nicht mit dem Programm angelegt – eine Verlängerung erstellt hier nur die Nebenabrede")
        self.tab2 = Tabelle(["Name", "Zimmer", "Beginn", "Ende", "Maßnahme"], ["l", "l", "l", "l", "l"], dehnen=0)
        self.tab2.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tab2.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tab2.cellDoubleClicked.connect(lambda r, _c: self._weitere_verlaengern(r))
        self.k_weitere.inhalt.addWidget(self.tab2)
        a2 = QHBoxLayout()
        b2 = knopf("Nebenabrede erstellen …", "ghost", "kalender")
        b2.clicked.connect(lambda: self._weitere_verlaengern(self.tab2.currentRow()))
        a2.addWidget(b2)
        a2.addStretch()
        self.k_weitere.inhalt.addLayout(a2)
        self.lay.addWidget(self.k_weitere)
        self.lay.addStretch()
        for k in self.findChildren(Karte):
            k.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        zustand.zimmer_geaendert.connect(self.anstossen)

    # ---- läuft auch ohne geladene Pivot -------------------------------------------------

    def anstossen(self) -> None:
        self._veraltet = True
        if sichtbar(self):
            self._ausfuehren()

    def showEvent(self, e):
        QWidget.showEvent(self, e)
        if self._veraltet:
            self._ausfuehren()

    def aktualisieren(self) -> None:
        heute = date.today()
        self._vertraege = sorted(mt.laden(), key=lambda m: (m.bis < heute, m.bis))
        try:
            self._weitere = mt.weitere_mieter(zp.laden(), heute)
        except Exception:          # noqa: BLE001 – ohne Gebäudeplan bleibt die zweite Liste leer
            self._weitere = []
        zeilen = []
        laufend = bald = 0
        for m in self._vertraege:
            text, stufe = mt.status(m, heute)
            laufend += stufe in ("ok", "knapp", "akzent")
            bald += stufe == "knapp"
            zeilen.append([m.nr, f"{m.nachname}, {m.vorname}", m.zimmer_kurz, f"{m.von:%d.%m.%Y}", f"{m.bis:%d.%m.%Y}",
                           f"{mt._euro(m.miete)} €", Pille(text, stufe),
                           f"{len(m.verlaengerungen)}×" if m.verlaengerungen else "–"])
        self.tab.fuellen(zeilen)
        self.tab.widgets_einpassen()
        self.tab.hoehe_anpassen(16)
        self.tab2.fuellen([[b.name, b.zimmer.removeprefix("GS-"), f"{b.von:%d.%m.%Y}", f"{b.bis:%d.%m.%Y}", b.massnahme]
                           for b in self._weitere])
        self.tab2.widgets_einpassen()
        self.tab2.hoehe_anpassen(16)
        self.hinweis.setVisible(not self._vertraege)
        self.k_vertraege.setVisible(bool(self._vertraege))
        self.k_weitere.setVisible(bool(self._weitere))
        leeren(self.kz)
        for text, stufe, tipp in ((f"{laufend} laufende{'r' if laufend == 1 else ''} Vertr{'ag' if laufend == 1 else 'äge'}", "ok", "mit dem Programm erstellt – gültig oder beginnt bald"),
                                  (f"{bald} {'endet' if bald == 1 else 'enden'} bald", "knapp" if bald else "neutral",
                                   f"in den nächsten {mt.BALD_TAGE // 7} Wochen – Zeit für eine Nebenabrede"),
                                  (f"{len(self._weitere)} weitere laut Gebäudeplan", "neutral",
                                   "Mieter, die nicht mit dem Programm angelegt wurden")):
            p = Pille(text, stufe)
            p.setToolTip(tipp)
            self.kz.addWidget(p)
        self.kz.addStretch()
        self._auswahl()

    def _gewaehlt(self) -> mt.Mietvertrag | None:
        r = self.tab.currentRow()
        if r < 0 or not self.tab.selectedItems():
            return None
        i = self.tab.daten_zeile(r)
        return self._vertraege[i] if 0 <= i < len(self._vertraege) else None

    def _auswahl(self) -> None:
        an = self._gewaehlt() is not None
        for b in (self.b_verl, self.b_neu_pdf, self.b_karte):
            b.setEnabled(an)

    # ---- Aktionen -----------------------------------------------------------------------

    def _neu(self) -> None:
        from ..mieter_dialog import NeuerMieterDialog

        if NeuerMieterDialog(self.z, parent=self.window()).exec():
            self.anstossen()

    def _verlaengern(self) -> None:
        from ..mieter_dialog import VerlaengernDialog

        if (mv := self._gewaehlt()) is not None and VerlaengernDialog(self.z, mv.nr, self.window()).exec():
            self.anstossen()

    def _weitere_verlaengern(self, r: int) -> None:
        from ..mieter_dialog import VerlaengernDialog

        if r < 0:
            return
        i = self.tab2.daten_zeile(r)
        if 0 <= i < len(self._weitere):
            b = self._weitere[i]
            VerlaengernDialog(self.z, "", self.window(), name=b.name, bis=b.bis).exec()

    def _unterlagen(self) -> None:
        from ..mieter_dialog import unterlagen_speichern

        mv = self._gewaehlt()
        if mv is None:
            return
        if (fehlt := mt.fehlende_vorlagen()):
            self.z.meldung.emit("Vorlagen fehlen im Ordner „Vorlagen/Mieter“: " + ", ".join(fehlt), "fehler")
            return
        try:
            erg = unterlagen_speichern(self.window(), mv)
        except OSError as e:
            self.z.meldung.emit(f"Konnte nicht speichern (ist die Datei noch geöffnet?): {e}", "fehler")
            return
        if erg is not None:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            self.z.meldung.emit(f"Unterlagen für MV {mv.nr} neu erstellt (aktueller Stand, Ende {mv.bis:%d.%m.%Y}).", "ok")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(erg[0])))

    def _oeffnen(self, r: int) -> None:
        from ..zimmerkarte import karte_oeffnen

        if r < 0:
            return
        i = self.tab.daten_zeile(r)
        if 0 <= i < len(self._vertraege):
            m = self._vertraege[i]
            karte_oeffnen(self.window(), self.z, m.zimmer, m.person)
