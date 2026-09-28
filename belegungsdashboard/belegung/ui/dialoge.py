"""Dialoge: Listen-Import mit Spaltenzuordnung und Pivot-Struktur."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLineEdit, QSpinBox, QVBoxLayout,
)
from openpyxl.utils import get_column_letter

from .. import importe, pivot
from ..konfig import STANDORT_LABEL, STANDORTE
from .basis import Worker
from .widgets import Hinweis, Karte, Pille, Tabelle, knopf, label, leeren


class ImportDialog(QDialog):
    def __init__(self, pfad: Path, art: str, parent=None):
        super().__init__(parent)
        self.pfad, self.art, self.anzahl = pfad, art, 0
        self.setWindowTitle(f"{importe.ARTEN[art]} importieren")
        self.resize(980, 720)
        self._eintraege: list[dict] = []

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        v.addWidget(label(f"{importe.ARTEN[art]} importieren", "seitentitel"))
        v.addWidget(label(f"{pfad.name} · Spalten wurden automatisch zugeordnet – bitte kurz prüfen. Ein Import "
                          f"ersetzt die bisher importierten {importe.ARTEN[art]} vollständig.", "muted", umbruch=True))

        try:
            self.tabelle = importe.tabelle_lesen(pfad)
        except Exception as exc:
            v.addWidget(Hinweis(f"Die Datei konnte nicht gelesen werden: {exc}", "fehler"))
            zu = knopf("Schließen")
            zu.clicked.connect(self.reject)
            v.addWidget(zu, 0, Qt.AlignRight)
            self.tabelle = None
            return
        self.zuordnung = importe.gemerkte_zuordnung(art, pfad.name) or importe.zuordnung_erraten(self.tabelle)
        if self.zuordnung.sheet and self.zuordnung.sheet != self.tabelle.sheet and self.zuordnung.sheet in self.tabelle.sheets:
            self.tabelle = importe.tabelle_lesen(pfad, self.zuordnung.sheet)

        einstellungen = Karte("Zuordnung")
        gitter = QGridLayout()
        gitter.setHorizontalSpacing(14)
        gitter.setVerticalSpacing(8)
        self.sheet = QComboBox()
        self.sheet.addItems(self.tabelle.sheets or ["(CSV)"])
        if self.tabelle.sheet:
            self.sheet.setCurrentText(self.tabelle.sheet)
        self.sheet.setEnabled(bool(self.tabelle.sheets))
        self.sheet.currentTextChanged.connect(self._sheet_wechsel)
        self.kopfzeile = QSpinBox()
        self.kopfzeile.setRange(1, max(1, len(self.tabelle.zeilen)))
        self.kopfzeile.setValue(self.zuordnung.kopfzeile + 1)
        self.kopfzeile.valueChanged.connect(self._kopf_wechsel)
        gitter.addWidget(label("Tabellenblatt", "klein"), 0, 0)
        gitter.addWidget(self.sheet, 1, 0)
        gitter.addWidget(label("Kopfzeile", "klein"), 0, 1)
        gitter.addWidget(self.kopfzeile, 1, 1)
        self.felder: dict[str, QComboBox] = {}
        for i, feld in enumerate(importe.FELDER):
            if art == "anreisen" and feld == "kategorie":
                continue
            cb = QComboBox()
            cb.setMinimumWidth(150)
            cb.currentIndexChanged.connect(self._vorschau)
            self.felder[feld] = cb
            spalte = 2 + len(self.felder) - 1
            gitter.addWidget(label(importe.FELD_LABEL[feld] + (" *" if feld == "von" else ""), "klein"), 0, spalte)
            gitter.addWidget(cb, 1, spalte)
        self.standort = QComboBox()
        self.standort.addItem("— Zeile überspringen —" if art == "anreisen" else "Goslar (Regel für Mieter)", None)
        for s in STANDORTE:
            self.standort.addItem(STANDORT_LABEL[s], s)
        if self.zuordnung.standard_standort:
            self.standort.setCurrentIndex(max(0, self.standort.findData(self.zuordnung.standard_standort)))
        self.standort.currentIndexChanged.connect(self._vorschau)
        gitter.addWidget(label("Standort, wenn leer/unbekannt", "klein"), 2, 0, 1, 2)
        gitter.addWidget(self.standort, 3, 0, 1, 2)
        self.dauer = QSpinBox()
        self.dauer.setRange(0, 60)
        self.dauer.setSuffix(" Monate")
        self.dauer.setSpecialValueText("nur als Termin")
        self.dauer.setValue(self.zuordnung.dauer_monate)
        self.dauer.valueChanged.connect(self._vorschau)
        if art == "anreisen":
            gitter.addWidget(label("Ohne Abreise: Aufenthaltsdauer", "klein"), 2, 2, 1, 2)
            gitter.addWidget(self.dauer, 3, 2, 1, 2)
        einstellungen.inhalt.addLayout(gitter)
        v.addWidget(einstellungen)

        vorschau = Karte("Vorschau")
        self.status = QHBoxLayout()
        vorschau.inhalt.addLayout(self.status)
        self.vorschau = Tabelle(["Von", "Bis", "Standort", "Anzahl", "Bezeichnung", "Kategorie"], ["l", "l", "l", "r", "l", "l"])
        vorschau.inhalt.addWidget(self.vorschau, 1)
        self.hinweise = label("", "klein", umbruch=True)
        vorschau.inhalt.addWidget(self.hinweise)
        v.addWidget(vorschau, 1)

        unten = QHBoxLayout()
        unten.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.clicked.connect(self.reject)
        self.ok = knopf("Importieren", "primary", "haken")
        self.ok.clicked.connect(self._importieren)
        unten.addWidget(abbrechen)
        unten.addWidget(self.ok)
        v.addLayout(unten)
        self._spalten_fuellen()
        self._vorschau()

    def _spalten_fuellen(self) -> None:
        kopf = self.tabelle.zeilen[self.zuordnung.kopfzeile] if self.tabelle.zeilen else []
        for feld, cb in self.felder.items():
            cb.blockSignals(True)
            cb.clear()
            cb.addItem("— nicht vorhanden —", None)
            for i, wert in enumerate(kopf):
                cb.addItem(f"{get_column_letter(i + 1)}: {wert if wert not in (None, '') else '(leer)'}", i)
            ziel = self.zuordnung.spalten.get(feld)
            cb.setCurrentIndex(cb.findData(ziel) if ziel is not None and cb.findData(ziel) >= 0 else 0)
            cb.blockSignals(False)

    def _sheet_wechsel(self, name: str) -> None:
        self.tabelle = importe.tabelle_lesen(self.pfad, name)
        self.zuordnung = importe.zuordnung_erraten(self.tabelle)
        self.kopfzeile.blockSignals(True)
        self.kopfzeile.setRange(1, max(1, len(self.tabelle.zeilen)))
        self.kopfzeile.setValue(self.zuordnung.kopfzeile + 1)
        self.kopfzeile.blockSignals(False)
        self._spalten_fuellen()
        self._vorschau()

    def _kopf_wechsel(self, wert: int) -> None:
        self.zuordnung.kopfzeile = wert - 1
        kopf = self.tabelle.zeilen[wert - 1]
        neu = importe.zuordnung_erraten(importe.Tabelle(self.pfad, [], None, [kopf]))
        self.zuordnung.spalten = neu.spalten
        self._spalten_fuellen()
        self._vorschau()

    def _vorschau(self, *_):
        self.zuordnung.spalten = {f: (self.felder[f].currentData() if f in self.felder else None) for f in importe.FELDER}
        self.zuordnung.standard_standort = self.standort.currentData()
        self.zuordnung.dauer_monate = self.dauer.value()
        self.zuordnung.sheet = self.tabelle.sheet
        leeren(self.status)
        try:
            self._eintraege, hinweise = importe.umwandeln(self.tabelle, self.zuordnung, self.art)
        except ValueError as exc:
            self._eintraege, hinweise = [], []
            self.status.addWidget(Pille(str(exc), "knapp"))
        n = len(self._eintraege)
        self.status.addWidget(Pille(f"{n} Einträge erkannt", "ok" if n else "neutral"))
        if hinweise:
            self.status.addWidget(Pille(f"{len(hinweise)} Zeile{'' if len(hinweise) == 1 else 'n'} übersprungen", "knapp"))
        if self._eintraege:
            summen = importe.standorte_in(self._eintraege)
            self.status.addWidget(label(" · ".join(f"{STANDORT_LABEL[s]} {v}" for s, v in summen.items()), "klein"))
        self.status.addStretch()
        self.hinweise.setText("<br>".join(hinweise[:6]) + (f"<br>… und {len(hinweise) - 6} weitere" if len(hinweise) > 6 else ""))
        self.vorschau.fuellen([[date.fromisoformat(e["von"]).strftime("%d.%m.%Y"),
                                "–" if e["nur_termin"] else ("offen" if e["bis"] >= "2099" else date.fromisoformat(e["bis"]).strftime("%d.%m.%Y")),
                                STANDORT_LABEL[e["standort"]], e["anzahl"], e["bezeichnung"] or "–", e["kategorie"]]
                               for e in self._eintraege[:100]])
        self.ok.setEnabled(n > 0)
        self.ok.setText(f"{n} Einträge importieren" if n else "Importieren")

    def _importieren(self) -> None:
        importe.datensatz_speichern(self.art, self.pfad, self.zuordnung, self._eintraege)
        self.anzahl = len(self._eintraege)
        self.accept()


class PivotProfilDialog(QDialog):
    """Aufbau einer Pivot-/Kreuztabellen-Datei festlegen, mit Live-Vorschau."""

    def __init__(self, pfad: Path, parent=None):
        super().__init__(parent)
        self.pfad = pfad
        self.setWindowTitle("Pivot-Struktur")
        self.resize(640, 620)
        self._profile, self._zuordnung = pivot.lade_profile()
        self._matrix: list | None = None
        aktuell = pivot.profil_fuer_datei(pfad.name)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Pivot-Struktur", "seitentitel"))
        v.addWidget(label(f"{pfad.name} – nur nötig, wenn eine Datei anders aufgebaut ist als üblich. Die Vorschau "
                          "zeigt sofort, ob die Einstellungen passen.", "muted", umbruch=True))
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        self.name = QLineEdit(aktuell.name)
        form.addRow("Profilname", self.name)
        self.modus = QComboBox()
        self.modus.addItem("Automatisch (erste echte Pivot-Tabelle)", "auto")
        self.modus.addItem("Festes Tabellenblatt (Kreuztabelle)", "manuell")
        self.modus.setCurrentIndex(0 if aktuell.sheet_modus == "auto" else 1)
        form.addRow("Tabellenblatt", self.modus)
        self.sheet = QComboBox()
        try:
            self.sheet.addItems(pivot.sheet_namen_datei(pfad))
        except Exception:
            pass
        if aktuell.sheet_name:
            self.sheet.setCurrentText(aktuell.sheet_name)
        form.addRow("Blattname", self.sheet)
        self.ausrichtung = QComboBox()
        self.ausrichtung.addItem("Standorte/Häuser in Spalten, Tage in Zeilen", "standard")
        self.ausrichtung.addItem("Gespiegelt: Standorte/Häuser in Zeilen, Tage in Spalten", "transponiert")
        self.ausrichtung.setCurrentIndex(0 if aktuell.ausrichtung == "standard" else 1)
        form.addRow("Ausrichtung", self.ausrichtung)
        self.ebenen = QComboBox()
        self.ebenen.addItem("Standort und Haus", 2)
        self.ebenen.addItem("Nur Standort", 1)
        self.ebenen.setCurrentIndex(0 if aktuell.hierarchie_ebenen == 2 else 1)
        form.addRow("Ebenen", self.ebenen)
        self.marker = QLineEdit(aktuell.kopfzeilen_marker)
        form.addRow("Kopfzeilen-Text", self.marker)
        self.suffix = QLineEdit(aktuell.zwischensummen_suffix)
        form.addRow("Zwischensummen-Endung", self.suffix)
        self.fmt = QLineEdit(aktuell.datumsformat)
        form.addRow("Datumsformat", self.fmt)
        v.addLayout(form)
        for w in (self.ausrichtung, self.ebenen):
            w.currentIndexChanged.connect(self._vorschau)
        for w in (self.marker, self.suffix, self.fmt):
            w.textChanged.connect(self._vorschau)
        self.modus.currentIndexChanged.connect(self._matrix_laden)
        self.sheet.currentIndexChanged.connect(self._matrix_laden)

        self.ergebnis = Karte("Vorschau")
        self.ergebnis_text = label("Datei wird gelesen …", "muted", umbruch=True)
        self.ergebnis.inhalt.addWidget(self.ergebnis_text)
        v.addWidget(self.ergebnis, 1)
        unten = QHBoxLayout()
        unten.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.clicked.connect(self.reject)
        self.ok = knopf("Speichern und anwenden", "primary", "haken")
        self.ok.clicked.connect(self._speichern)
        unten.addWidget(abbrechen)
        unten.addWidget(self.ok)
        v.addLayout(unten)
        self._matrix_laden()

    def _profil(self) -> pivot.PivotProfil:
        return pivot.PivotProfil(
            name=self.name.text().strip() or "Profil", sheet_modus=self.modus.currentData(),
            sheet_name=self.sheet.currentText() or None, ausrichtung=self.ausrichtung.currentData(),
            hierarchie_ebenen=self.ebenen.currentData(), kopfzeilen_marker=self.marker.text() or "Zeilenbeschriftungen",
            zwischensummen_suffix=self.suffix.text(), datumsformat=self.fmt.text() or "%d.%m.%Y",
        )

    def _matrix_laden(self, *_):
        self.sheet.setEnabled(self.modus.currentData() == "manuell")
        self.ergebnis_text.setText("Datei wird gelesen …")
        self._w = Worker(pivot.lese_matrix_datei, self.pfad, self._profil(), parent=self)
        self._w.fertig.connect(self._matrix_da)
        self._w.fehler.connect(lambda t: self.ergebnis_text.setText(f"Datei konnte nicht gelesen werden: {t}"))
        self._w.start()

    def _matrix_da(self, ergebnis) -> None:
        self._matrix = ergebnis[0]
        self._vorschau()

    def _vorschau(self, *_):
        if self._matrix is None:
            return
        r = pivot.vorschau(self._matrix, self._profil())
        if not r["erfolg"]:
            self.ergebnis_text.setText(f"<b>Passt nicht:</b> {r['fehler']}")
            self.ok.setEnabled(False)
            return
        self.ok.setEnabled(True)
        haeuser = "<br>".join(f"<b>{STANDORT_LABEL[s]}</b>: {', '.join(h) or '—'}" for s, h in r["haeuser_je_standort"].items())
        self.ergebnis_text.setText(f"✓ {r['anzahl_tage']} Tage vom {r['erster_tag']:%d.%m.%Y} bis {r['letzter_tag']:%d.%m.%Y}<br><br>{haeuser}")

    def _speichern(self) -> None:
        p = self._profil()
        self._profile[p.name] = p
        self._zuordnung[self.pfad.name.lower()] = p.name
        pivot.speichere_profile(self._profile, self._zuordnung)
        self.accept()
