"""Masken „Neuer Mieter“ (alle Unterlagen als eine PDF + Eintrag im Zimmerplan) und „Mietvertrag verlängern“
(Nebenabrede als Word-Datei und PDF). Die Logik steht in ``belegung/mieter.py``.
"""

from __future__ import annotations

import tempfile
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QLocale, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QSpinBox,
    QVBoxLayout,
)

from .. import mieter as mt
from .. import speicher
from .. import zimmerplan as zp
from .widgets import DatumFeld, Hinweis, Segment, knopf, label

ANREDEN = ["Frau", "Herr"]


def _ordner_start() -> Path:
    return Path(speicher.einstellungen().get("export_ordner") or Path.home())


def _html_als_pdf(html: str) -> bytes:
    """HTML (QTextDocument) als PDF-Bytes – wie alle anderen Drucklisten."""
    from PySide6.QtPrintSupport import QPrinter

    from .drucken import dokument_drucken

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "dokument.pdf"
        drucker = QPrinter(QPrinter.HighResolution)
        drucker.setOutputFormat(QPrinter.PdfFormat)
        drucker.setOutputFileName(str(pfad))
        dokument_drucken(drucker, html, False)
        return pfad.read_bytes()


def _vorlagen_hinweis() -> Hinweis | None:
    fehlt = mt.fehlende_vorlagen()
    if not fehlt:
        return None
    return Hinweis("Vorlagen fehlen im Ordner „Vorlagen/Mieter“ neben dem Programm: " + ", ".join(fehlt)
                   + ". Bitte das aktuelle Update-Paket entpacken.", "fehler")


def unterlagen_speichern(eltern, mv: mt.Mietvertrag) -> tuple[Path, list[str]] | None:
    """Speicherort fragen, Vertrag setzen und alle Vordrucke in eine PDF. None = abgebrochen."""
    name = f"Mietunterlagen_MV{mv.nr}_{mv.nachname.replace(' ', '_')}.pdf"
    pfad, _ = QFileDialog.getSaveFileName(eltern, "Mietunterlagen speichern", str(_ordner_start() / name), "PDF (*.pdf)")
    if not pfad:
        return None
    ziel = Path(pfad if pfad.lower().endswith(".pdf") else pfad + ".pdf")
    speicher.einstellung_setzen("export_ordner", str(ziel.parent))
    ordner = mt.vorlagen_ordner()
    vorlage = (ordner / mt.VERTRAG).read_text(encoding="utf-8")
    vertrag = _html_als_pdf(mt.vertrag_html(mv, vorlage, ordner / mt.LOGO))
    return ziel, mt.paket_erstellen(mv, vertrag, ziel, ordner)


class NeuerMieterDialog(QDialog):
    """Name, Zimmer, ab wann – der Rest ist vorgeschlagen und änderbar."""

    def __init__(self, zustand, zimmer: str = "", parent=None):
        super().__init__(parent)
        self.z = zustand
        self.stand = zp.laden()
        self._ende_von_hand = False
        self.setWindowTitle("Neuer Mieter")
        self.setMinimumWidth(600)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Neuer Mieter", "seitentitel"))
        v.addWidget(label("Erstellt in einer PDF: Mietvertrag, Wohnungsgeberbestätigung, SEPA-Lastschriftmandat und "
                          "Mietschuldenfreiheitsbescheinigung – und trägt den Mieter im Zimmerplan ein.", "muted",
                          umbruch=True))
        if (h := _vorlagen_hinweis()) is not None:
            v.addWidget(h)

        r = QGridLayout()
        r.setHorizontalSpacing(12)
        r.setVerticalSpacing(10)
        zeile = 0

        def feld(text: str, w, tipp: str = "") -> None:
            nonlocal zeile
            r.addWidget(label(text, "fett"), zeile, 0)
            r.addWidget(w, zeile, 1, Qt.AlignLeft | Qt.AlignVCenter)
            if tipp:
                r.addWidget(label(tipp, "klein", umbruch=True), zeile, 2)
            zeile += 1

        self.anrede = Segment(ANREDEN, 0)
        feld("Anrede", self.anrede, "„Mieterin“ oder „Mieter“ im Vertrag")
        self.vorname = QLineEdit()
        self.vorname.setPlaceholderText("Vorname")
        feld("Vorname", self.vorname)
        self.nachname = QLineEdit()
        self.nachname.setPlaceholderText("Nachname")
        feld("Nachname", self.nachname)
        heute = date.today()
        start = heute.replace(day=1) + timedelta(days=32)
        self.von = DatumFeld(start.replace(day=1))
        self.von.geaendert.connect(self._beginn_geaendert)
        feld("Mietbeginn", self.von)
        self.bis = DatumFeld(mt.standard_ende(self.von.datum()))
        self.bis.geaendert.connect(lambda _d: setattr(self, "_ende_von_hand", True))
        feld("Mietende", self.bis, f"Vorschlag: {mt.STANDARD_MONATE} Monate")
        zz = QHBoxLayout()
        self.zimmer = QComboBox()
        self.zimmer.setMinimumWidth(240)
        zz.addWidget(self.zimmer, 1)
        self.alle = QCheckBox("alle Zimmer")
        self.alle.setToolTip("Auch Zimmer außerhalb der Mieter-Regel (Haus 6) oder belegte zeigen – mit Warnung")
        self.alle.toggled.connect(lambda _a: self._zimmer_fuellen())
        zz.addWidget(self.alle)
        r.addWidget(label("Zimmer", "fett"), zeile, 0)
        r.addLayout(zz, zeile, 1, 1, 2)
        zeile += 1
        self.miete = QDoubleSpinBox()
        self.miete.setRange(0, 5000)
        self.miete.setDecimals(2)
        self.miete.setSuffix(" €")
        self.miete.setLocale(QLocale(QLocale.German, QLocale.Germany))
        self.miete.setMinimumWidth(140)
        self.miete.setValue(mt.STANDARD_MIETE)
        feld("Mietzins / Monat", self.miete)
        self.flaeche = QSpinBox()
        self.flaeche.setRange(1, 200)
        self.flaeche.setSuffix(" m²")
        self.flaeche.setValue(mt.STANDARD_FLAECHE)
        feld("Wohnfläche ca.", self.flaeche)
        self.schluessel = QSpinBox()
        self.schluessel.setRange(1, 9)
        feld("Schlüssel", self.schluessel)
        kz = QHBoxLayout()
        kz.setSpacing(10)
        self.mit_kaution = QCheckBox("vereinbaren")
        self.mit_kaution.setToolTip("Mietsicherheit von einer Monatsmiete (§ Mietsicherheit im Vertrag). "
                                    "Ohne Häkchen entfällt der Paragraf.")
        kz.addWidget(self.mit_kaution)
        self.kaution = DatumFeld(self.von.datum())
        self.kaution.setEnabled(False)
        self.mit_kaution.toggled.connect(self.kaution.setEnabled)
        kz.addWidget(label("zahlbar bis", "klein"))
        kz.addWidget(self.kaution)
        kz.addStretch()
        r.addWidget(label("Kaution", "fett"), zeile, 0)
        r.addLayout(kz, zeile, 1, 1, 2)
        zeile += 1
        self.nr = QLineEdit(mt.naechste_nummer())
        self.nr.setMaximumWidth(120)
        feld("Vertragsnummer", self.nr, "zählt automatisch weiter")
        r.setColumnStretch(2, 1)
        v.addLayout(r)
        if not mt.laden():                       # erster Vertrag mit dem Programm: Nummernkreis abgleichen
            v.addWidget(label("Erster Mietvertrag aus dem Programm: Bitte die Vertragsnummer einmal mit der zuletzt "
                              "vergebenen abgleichen (z. B. 26-010 → 26-011) – danach zählt sie von selbst weiter.",
                              "klein", umbruch=True))
        self.warnung = label("", "klein", umbruch=True)
        v.addWidget(self.warnung)
        self.zimmer.currentIndexChanged.connect(lambda _i: self._pruefen_zimmer())

        unten = QHBoxLayout()
        unten.addStretch()
        ab = knopf("Abbrechen", "ghost")
        ab.clicked.connect(self.reject)
        unten.addWidget(ab)
        self.ok = knopf("Unterlagen erstellen (PDF)", "primary", "drucker")
        self.ok.clicked.connect(self._erstellen)
        unten.addWidget(self.ok)
        v.addLayout(unten)
        self._vorwahl = zimmer
        self._zimmer_fuellen()

    def _beginn_geaendert(self, d: date) -> None:
        if not self._ende_von_hand:
            self.bis.setzen(mt.standard_ende(d))
        self.kaution.setzen(d)
        self._zimmer_fuellen()

    def _bedarf(self) -> zp.Bedarf:
        return zp.Bedarf("mv:neu", "Neu", "Miete Goslar", "Mieter", self.von.datum(), self.bis.datum(),
                         "w" if self.anrede.index() == 0 else "m")

    def _zimmer_fuellen(self) -> None:
        vorher = self.zimmer.currentData() or self._vorwahl
        self.zimmer.blockSignals(True)
        self.zimmer.clear()
        b = self._bedarf()
        lage = self.stand.lage
        for z in sorted((z for z in self.stand.zimmer if z.aktiv), key=lambda z: (zp._haus_sort(z.haus), z.nummer)):
            grund = zp.passt(lage, z, b)
            if grund is None or self.alle.isChecked():
                self.zimmer.addItem(z.kurz + ("" if grund is None else f"  ({grund})"), z.id)
        i = self.zimmer.findData(vorher)
        self.zimmer.setCurrentIndex(max(i, 0))
        self.zimmer.blockSignals(False)
        if self.zimmer.count() == 0:
            self.warnung.setText("Im Zeitraum ist kein passendes Zimmer frei – „alle Zimmer“ zeigt auch andere.")
        self._pruefen_zimmer()

    def _pruefen_zimmer(self) -> None:
        zid = self.zimmer.currentData()
        if not zid:
            return
        grund = zp.passt(self.stand.lage, self.stand.lage.zimmer[zid], self._bedarf())
        self.warnung.setText(f"Achtung: {grund}" if grund else "")

    def _vertrag(self) -> mt.Mietvertrag:
        return mt.Mietvertrag(self.nr.text().strip(), ANREDEN[self.anrede.index()], self.vorname.text().strip(),
                              self.nachname.text().strip(), self.zimmer.currentData() or "", self.von.datum(),
                              self.bis.datum(), round(self.miete.value(), 2), self.flaeche.value(),
                              self.schluessel.value(), self.kaution.datum() if self.mit_kaution.isChecked() else None,
                              kaution=self.mit_kaution.isChecked())

    def _erstellen(self) -> None:
        mv = self._vertrag()
        fehler = mt.pruefen(mv) + [f"Vorlage fehlt: {v}" for v in mt.fehlende_vorlagen()]
        if fehler:
            self.warnung.setText("<b>Bitte prüfen:</b> " + " ".join(fehler))
            return
        try:
            erg = unterlagen_speichern(self, mv)
        except OSError as e:
            self.warnung.setText(f"Konnte nicht speichern (ist die Datei noch geöffnet?): {e}")
            return
        if erg is None:
            return
        ziel, teile = erg
        mt.anlegen(mv)
        self.z.zimmer_geaendert.emit()
        self.z.meldung.emit(f"Mietvertrag {mv.nr} für {mv.name} ({mv.zimmer_kurz}) erstellt: " + ", ".join(teile)
                            + ". Im Zimmerplan als Mieter eingetragen.", "ok")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ziel)))
        self.accept()


class VerlaengernDialog(QDialog):
    """Mieter wählen (oder von Hand), neues Ende → Nebenabrede als .docx und .pdf; Zimmerplan zieht mit."""

    def __init__(self, zustand, nr: str = "", parent=None, name: str = "", bis: date | None = None):
        super().__init__(parent)
        self.z = zustand
        self._hand_bis = bis
        self.mieter = sorted(mt.laden(), key=lambda m: m.bis)
        self.setWindowTitle("Mietvertrag verlängern")
        self.setMinimumWidth(520)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Mietvertrag verlängern", "seitentitel"))
        v.addWidget(label("Erstellt die Nebenabrede als Word-Datei (zum Bearbeiten) und als PDF. Bei Mietern aus dieser "
                          "Liste wird das Ende auch im Zimmerplan verschoben.", "muted", umbruch=True))
        r = QGridLayout()
        r.setHorizontalSpacing(12)
        r.setVerticalSpacing(10)
        self.wahl = QComboBox()
        for m in self.mieter:
            self.wahl.addItem(f"MV {m.nr} · {m.nachname}, {m.vorname} · {m.zimmer_kurz} · bis {m.bis:%d.%m.%Y}", m.nr)
        self.wahl.addItem("Anderer Mieter (von Hand eingeben) …", "")
        r.addWidget(label("Mieter", "fett"), 0, 0)
        r.addWidget(self.wahl, 0, 1, 1, 3)
        self.hand_nr = QLineEdit()
        self.hand_nr.setPlaceholderText("Vertragsnr., z. B. 25-007")
        self.hand_anrede = QComboBox()
        self.hand_anrede.addItems(ANREDEN)
        self.hand_vorname = QLineEdit()
        self.hand_vorname.setPlaceholderText("Vorname")
        self.hand_nachname = QLineEdit()
        self.hand_nachname.setPlaceholderText("Nachname")
        self.hand = [self.hand_nr, self.hand_anrede, self.hand_vorname, self.hand_nachname]
        r.addWidget(self.hand_nr, 1, 1)
        r.addWidget(self.hand_anrede, 1, 2)
        r.addWidget(self.hand_vorname, 2, 1)
        r.addWidget(self.hand_nachname, 2, 2, 1, 2)
        self.bisher = label("", "muted")
        r.addWidget(label("Bisher bis", "fett"), 3, 0)
        r.addWidget(self.bisher, 3, 1, 1, 3)
        self.bis = DatumFeld(date.today())
        r.addWidget(label("Verlängern bis", "fett"), 4, 0)
        r.addWidget(self.bis, 4, 1)
        v.addLayout(r)
        self.warnung = label("", "klein", umbruch=True)
        v.addWidget(self.warnung)
        unten = QHBoxLayout()
        unten.addStretch()
        ab = knopf("Abbrechen", "ghost")
        ab.clicked.connect(self.reject)
        unten.addWidget(ab)
        ok = knopf("Nebenabrede erstellen", "primary", "drucker")
        ok.clicked.connect(self._erstellen)
        unten.addWidget(ok)
        v.addLayout(unten)
        self.wahl.currentIndexChanged.connect(lambda _i: self._gewaehlt())
        if nr:
            self.wahl.setCurrentIndex(max(self.wahl.findData(nr), 0))
        elif name:                                  # Mieter laut Zimmerplan, nicht hier angelegt: von Hand vorbelegt
            self.wahl.setCurrentIndex(self.wahl.count() - 1)
            nach, _, vor = name.partition(",")
            self.hand_nachname.setText(nach.strip())
            self.hand_vorname.setText(vor.strip())
        self._gewaehlt()

    def _aktuell(self) -> mt.Mietvertrag | None:
        nr = self.wahl.currentData()
        return next((m for m in self.mieter if m.nr == nr), None)

    def _gewaehlt(self) -> None:
        mv = self._aktuell()
        for w in self.hand:
            w.setVisible(mv is None)
        if mv is not None:
            self.bisher.setText(f"{mv.bis:%d.%m.%Y}")
            self.bis.setzen(mt.standard_ende(mv.bis + timedelta(days=1)))
        else:
            bisher = self._hand_bis
            self.bisher.setText((f"{bisher:%d.%m.%Y} laut Zimmerplan – " if bisher else "– ")
                                + "nur die Nebenabrede, der Zimmerplan bleibt")
            self.bis.setzen(mt.standard_ende((bisher + timedelta(days=1)) if bisher else date.today()))

    def _erstellen(self) -> None:
        mv = self._aktuell()
        bis_neu = self.bis.datum()
        if mv is None:
            if not (self.hand_nr.text().strip() and self.hand_nachname.text().strip()):
                self.warnung.setText("Bitte Vertragsnummer und Nachname eingeben.")
                return
            mv = mt.Mietvertrag(self.hand_nr.text().strip(), self.hand_anrede.currentText(),
                                self.hand_vorname.text().strip(), self.hand_nachname.text().strip(), "", date.today(),
                                bis_neu)
        elif bis_neu <= mv.bis:
            self.warnung.setText(f"Das neue Ende muss nach dem {mv.bis:%d.%m.%Y} liegen.")
            return
        name = f"Nebenabrede_MV{mv.nr}_{mv.nachname.replace(' ', '_')}.docx"
        pfad, _ = QFileDialog.getSaveFileName(self, "Nebenabrede speichern", str(_ordner_start() / name),
                                              "Word (*.docx)")
        if not pfad:
            return
        ziel = Path(pfad if pfad.lower().endswith(".docx") else pfad + ".docx")
        speicher.einstellung_setzen("export_ordner", str(ziel.parent))
        ordner = mt.vorlagen_ordner()
        logo = ordner / mt.LOGO if ordner else None
        try:
            ziel.write_bytes(mt.nebenabrede_docx(mv, bis_neu, logo))
            ziel.with_suffix(".pdf").write_bytes(_html_als_pdf(mt.nebenabrede_html(mv, bis_neu, logo)))
        except OSError as e:
            self.warnung.setText(f"Konnte nicht speichern (ist die Datei noch geöffnet?): {e}")
            return
        if self._aktuell() is not None:
            mt.verlaengern(mv.nr, bis_neu)
            self.z.zimmer_geaendert.emit()
        self.z.meldung.emit(f"Nebenabrede für MV {mv.nr} ({mv.name}) bis {bis_neu:%d.%m.%Y} gespeichert (Word + PDF)"
                            + (" – Zimmerplan verlängert." if self._aktuell() is not None else "."), "ok")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ziel)))
        self.accept()
