"""Daten & Import: Pivot-Quelle, Kapazitäten, Mieten, Anreisen, manuelle Einträge."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QSpinBox, QWidget

from ... import importe, laden, speicher
from ...konfig import MANUELLE_KATEGORIEN, STANDORT_LABEL, STANDORTE
from ..basis import Seite, Zustand
from ..widgets import DatumFeld, Karte, Leer, Pille, Tabelle, knopf, label, leeren, zahl


class DatenSeite(Seite):
    titel = "Daten & Import"
    untertitel = "Quelle, Kapazitäten und Listen pflegen"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        # Quelle
        self.quelle_karte = Karte("Pivot-Quelle", "Tägliche Reha-Belegung je Haus aus dem Rios-Cube")
        self.quelle_text = label("", "muted", umbruch=True)
        self.quelle_karte.inhalt.addWidget(self.quelle_text)
        knoepfe = QHBoxLayout()
        b_datei = knopf("Andere Datei wählen", None, "datei")
        b_datei.clicked.connect(lambda: self.window().datei_waehlen())
        b_profil = knopf("Pivot-Struktur …", "ghost", "tabelle", "Für Dateien mit abweichendem Aufbau")
        b_profil.clicked.connect(self._profil)
        b_neu = knopf("Neu einlesen", "ghost", "aktualisieren")
        b_neu.clicked.connect(lambda: self.z.neu_laden.emit(False))
        self.b_server = knopf("Vom Server abrufen", "ghost", "server", "OLAP-Refresh über Excel (nur Windows, Netz/VPN nötig)")
        self.b_server.clicked.connect(lambda: self.z.neu_laden.emit(True))
        self.b_server.setEnabled(laden.refresh_moeglich())
        for b in (b_datei, b_profil, b_neu, self.b_server):
            knoepfe.addWidget(b)
        knoepfe.addStretch()
        self.quelle_karte.inhalt.addLayout(knoepfe)

        # Kapazitäten
        self.kap_karte = Karte("Kapazitäten", "Netto = Reha und Verträge · Brutto = zusätzlich FRAI, Jugendhilfe, andere Bereiche")
        gitter = QGridLayout()
        gitter.setHorizontalSpacing(14)
        gitter.setVerticalSpacing(8)
        gitter.addWidget(label("Netto", "klein"), 0, 1)
        gitter.addWidget(label("Brutto", "klein"), 0, 2)
        self.kap_felder: dict[str, tuple[QSpinBox, QSpinBox]] = {}
        for i, s in enumerate(STANDORTE, start=1):
            gitter.addWidget(label(STANDORT_LABEL[s], "fett"), i, 0)
            n, b = QSpinBox(), QSpinBox()
            for f in (n, b):
                f.setRange(0, 5000)
                f.setFixedWidth(96)
            gitter.addWidget(n, i, 1)
            gitter.addWidget(b, i, 2)
            self.kap_felder[s] = (n, b)
        gitter.setColumnStretch(3, 1)
        self.kap_karte.inhalt.addLayout(gitter)
        speichern = knopf("Kapazitäten speichern", "primary", "haken")
        speichern.clicked.connect(self._kap_speichern)
        self.kap_karte.inhalt.addWidget(speichern, 0)
        self.zeile(self.quelle_karte, self.kap_karte, stretch=[3, 2])

        # Importe
        self.import_karten: dict[str, tuple[Karte, object]] = {}
        zeile = []
        for art, titel, text in (
            ("mieten", "Mieten", "Mietverträge (Von, Bis, Standort, Plätze, Mieter). Zählen zur Netto-Belegung."),
            ("anreisen", "Anreisen", "Geplante Neuaufnahmen (Anreise, ggf. Abreise, Standort, Anzahl). Ergänzen Belegung "
                                     "und Prognose ab morgen – vergangene Tage stehen bereits in der Pivot."),
        ):
            karte = Karte(titel, text)
            hoch = knopf("Excel hochladen", "primary", "hochladen")
            hoch.clicked.connect(lambda _=False, a=art: self._import(a))
            karte.aktion(hoch)
            inhalt = QWidget()
            inhalt_lay = QGridLayout(inhalt)
            inhalt_lay.setContentsMargins(0, 0, 0, 0)
            karte.inhalt.addWidget(inhalt)
            self.import_karten[art] = (karte, inhalt_lay)
            zeile.append(karte)
        self.zeile(*zeile)

        # Manuelle Einträge
        self.man_karte = Karte("Manuelle Einträge", "Einzelne Belegungen ohne Liste, z. B. DRK, Landkreis, FRAI, Jugendhilfe")
        form = QHBoxLayout()
        form.setSpacing(8)
        self.m_kat = QComboBox()
        self.m_kat.addItems(MANUELLE_KATEGORIEN)
        self.m_ort = QComboBox()
        for s in STANDORTE:
            self.m_ort.addItem(STANDORT_LABEL[s], s)
        heute = date.today()
        self.m_von = DatumFeld(heute)
        self.m_bis = DatumFeld(date(heute.year + 1, heute.month, min(heute.day, 28)))
        self.m_anzahl = QSpinBox()
        self.m_anzahl.setRange(1, 999)
        self.m_anzahl.setFixedWidth(70)
        self.m_text = QLineEdit()
        self.m_text.setPlaceholderText("Bezeichnung (optional)")
        plus = knopf("Hinzufügen", "primary", "plus")
        plus.clicked.connect(self._man_hinzufuegen)
        for w in (self.m_kat, self.m_ort, self.m_von, label("bis", "muted"), self.m_bis, label("Anzahl", "muted"),
                  self.m_anzahl, self.m_text):
            form.addWidget(w)
        form.addWidget(plus)
        self.man_karte.inhalt.addLayout(form)
        self.man_tabelle = Tabelle(["Kategorie", "Standort", "Von", "Bis", "Anzahl", "Bezeichnung", ""],
                                   ["l", "l", "l", "l", "r", "l", "l"])
        self.man_karte.inhalt.addWidget(self.man_tabelle)
        self.lay.addWidget(self.man_karte)
        self.lay.addStretch()

    # ---- Anzeige ------------------------------------------------------------------------

    def aktualisieren(self) -> None:
        ds = self.z.ds
        abruf = f"Pivot zuletzt vom Server abgerufen am {ds.pivot.abrufdatum:%d.%m.%Y}" if ds.pivot.abrufdatum else "Abrufdatum unbekannt"
        self.quelle_text.setText(
            f"<b>{ds.quelle}</b><br>{abruf}. Daten vom {ds.erster_tag:%d.%m.%Y} bis {ds.letzter_tag:%d.%m.%Y}; "
            f"Ist-Werte bis {ds.stichtag:%d.%m.%Y}, danach gebuchter Bestand. {len(ds.pivot.haus_standort)} Häuser erkannt.")
        for s, (n, b) in self.kap_felder.items():
            n.setValue(ds.kapazitaet(s))
            b.setValue(ds.kapazitaet(s, True))
        for art in importe.ARTEN:
            self._import_anzeigen(art)
        self._man_anzeigen()

    def _import_anzeigen(self, art: str) -> None:
        karte, lay = self.import_karten[art]
        leeren(lay)
        meta = self.z.ds.importe.get(art)
        if not meta:
            leer = Leer("hochladen", f"Noch keine {importe.ARTEN[art]} importiert",
                        "Excel- oder CSV-Datei wählen – Spalten werden automatisch erkannt und können vor dem Import "
                        "geprüft werden.")
            lay.addWidget(leer, 0, 0)
            return
        eintraege = self.z.ds.eintraege_von(quelle=art)
        zeit = datetime.fromisoformat(meta["importiert_am"]).strftime("%d.%m.%Y %H:%M")
        kopf = QHBoxLayout()
        kopf.addWidget(Pille(f"{meta['anzahl']} Einträge", "akzent"))
        kopf.addWidget(label(f"{meta['quelle']} · importiert {zeit}", "klein"))
        kopf.addStretch()
        weg = knopf("Entfernen", "gefahr", "loeschen")
        weg.clicked.connect(lambda: self._import_loeschen(art))
        kopf.addWidget(weg)
        lay.addLayout(kopf, 0, 0)
        tab = Tabelle(["Von", "Bis", "Standort", "Anzahl", "Bezeichnung"], ["l", "l", "l", "r", "l"])
        heute = date.today()
        sortiert = sorted(eintraege, key=lambda e: (e.bis < heute, e.von))
        tab.fuellen([[e.von.strftime("%d.%m.%Y"), "–" if e.nur_termin else ("offen" if e.bis.year >= 2099 else e.bis.strftime("%d.%m.%Y")),
                      STANDORT_LABEL[e.standort], e.anzahl, e.bezeichnung or "–"] for e in sortiert[:200]])
        tab.hoehe_anpassen(8)
        lay.addWidget(tab, 1, 0)
        summen = importe.standorte_in([{"standort": e.standort, "anzahl": e.anzahl} for e in eintraege])
        lay.addWidget(label(" · ".join(f"{STANDORT_LABEL[s]}: {zahl(v)}" for s, v in summen.items()), "klein"), 2, 0)

    def _man_anzeigen(self) -> None:
        roh = laden.manuelle_laden()
        zeilen = []
        for i, e in enumerate(roh):
            weg = knopf("", "icon", "loeschen", "Eintrag löschen")
            weg.clicked.connect(lambda _=False, i=i: self._man_loeschen(i))
            zeilen.append([e.get("typ") or e.get("kategorie"), STANDORT_LABEL.get(e["standort"], e["standort"]),
                           date.fromisoformat(e["von"]).strftime("%d.%m.%Y"), date.fromisoformat(e["bis"]).strftime("%d.%m.%Y"),
                           e["anzahl"], e.get("bezeichnung") or "–", weg])
        self.man_tabelle.fuellen(zeilen)
        self.man_tabelle.hoehe_anpassen(10)
        self.man_tabelle.setVisible(bool(zeilen))

    # ---- Aktionen ----------------------------------------------------------------------

    def _kap_speichern(self) -> None:
        werte = {s: {"netto": n.value(), "brutto": max(b.value(), n.value())} for s, (n, b) in self.kap_felder.items()}
        laden.kapazitaeten_speichern(werte)
        self.z.meldung.emit("Kapazitäten gespeichert.", "ok")
        self.z.listen_geaendert.emit()

    def _import(self, art: str) -> None:
        from ..dialoge import ImportDialog

        start = speicher.einstellungen().get(f"import_ordner_{art}") or str(Path.home())
        pfad, _ = QFileDialog.getOpenFileName(self, f"{importe.ARTEN[art]}-Liste wählen", start,
                                              "Tabellen (*.xlsx *.xlsm *.csv);;Alle Dateien (*)")
        if not pfad:
            return
        speicher.einstellung_setzen(f"import_ordner_{art}", str(Path(pfad).parent))
        dialog = ImportDialog(Path(pfad), art, self)
        if dialog.exec():
            self.z.meldung.emit(f"{dialog.anzahl} {importe.ARTEN[art]} importiert.", "ok")
            self.z.listen_geaendert.emit()

    def _import_loeschen(self, art: str) -> None:
        if QMessageBox.question(self, "Import entfernen", f"Alle importierten {importe.ARTEN[art]} entfernen?") != QMessageBox.Yes:
            return
        importe.datensatz_loeschen(art)
        self.z.listen_geaendert.emit()

    def _man_hinzufuegen(self) -> None:
        von, bis = self.m_von.datum(), self.m_bis.datum()
        if bis < von:
            self.z.meldung.emit("„Bis“ liegt vor „Von“.", "warnung")
            return
        roh = laden.manuelle_laden()
        roh.append({"typ": self.m_kat.currentText(), "standort": self.m_ort.currentData(), "von": von.isoformat(),
                    "bis": bis.isoformat(), "anzahl": self.m_anzahl.value(), "bezeichnung": self.m_text.text().strip()})
        laden.manuelle_speichern(roh)
        self.m_text.clear()
        self.z.meldung.emit("Eintrag gespeichert.", "ok")
        self._man_anzeigen()
        self.z.listen_geaendert.emit()

    def _man_loeschen(self, index: int) -> None:
        roh = laden.manuelle_laden()
        if 0 <= index < len(roh):
            del roh[index]
            laden.manuelle_speichern(roh)
            self._man_anzeigen()
            self.z.listen_geaendert.emit()

    def _profil(self) -> None:
        from ..dialoge import PivotProfilDialog

        if self.z.quelle is None:
            return
        if PivotProfilDialog(self.z.quelle, self).exec():
            self.z.neu_laden.emit(False)
