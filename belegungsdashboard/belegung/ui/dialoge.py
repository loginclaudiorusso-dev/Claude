"""Dialoge: Listen-Import, Anreiselisten, UWT, Abreise/Erinnerung und Pivot-Struktur."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout,
)
from openpyxl.utils import get_column_letter

from .. import anreiseliste, erinnerung, importe, pivot, speicher, uwt
from ..konfig import STANDORT_LABEL, STANDORTE
from .basis import Worker
from .widgets import DatumFeld, Hinweis, Karte, Pille, Tabelle, knopf, label, leeren


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


# ---------------------------------------------------------------------------------------
# Anreiselisten Goslar
# ---------------------------------------------------------------------------------------

def _d(x: date | None) -> str:
    return x.strftime("%d.%m.%Y") if x else "–"


class AnreiselistenDialog(QDialog):
    """Vorschau für eine oder mehrere Anreiselisten (Goslar) vor dem Import."""

    def __init__(self, pfade: list[Path], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anreiselisten importieren")
        self.resize(980, 760)
        self.bericht = anreiseliste.Bericht()
        self._listen: list[anreiseliste.Anreiseliste] = []
        fehler = []
        for p in pfade:
            try:
                self._listen.append(anreiseliste.liste_lesen(p))
            except Exception as exc:
                fehler.append(f"<b>{p.name}</b>: {exc}")

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        v.addWidget(label("Anreiselisten importieren", "seitentitel"))
        v.addWidget(label("Internat Goslar. Das Anreisedatum kommt aus dem Titel der Liste. Personen werden über die "
                          "TN-ID wiedererkannt – eingetragene Abreisen und Erinnerungen bleiben bei einem erneuten "
                          "Upload erhalten. Zur Belegung zählen nur Personen mit Internat „ja“.", "muted", umbruch=True), 0)
        for f in fehler:
            v.addWidget(Hinweis(f, "fehler"))

        bestand = {p.schluessel: p for p in anreiseliste.laden()[0]}
        listen = Karte("Listen")
        lt = Tabelle(["Datei", "Anreise", "Gruppe", "Personen", "mit Internat", "Status"], ["l", "l", "l", "r", "r", "l"], dehnen=0)
        lt.fuellen([[l.datei, _d(l.datum), l.gruppe, len(l.personen), l.mit_internat,
                     "bereits importiert – wird aktualisiert" if any(p.liste == l.schluessel for p in bestand.values()) else "neu"]
                    for l in self._listen])
        lt.hoehe_anpassen(6)
        listen.inhalt.addWidget(lt)
        v.addWidget(listen)

        personen = Karte("Personen")
        pt = Tabelle(["Anreise", "Name", "Maßnahme", "Internat", "Abreise", ""], ["l", "l", "l", "l", "l", "l"], dehnen=1)
        zeilen, hinweise = [], []
        for l in self._listen:
            hinweise += [f"{l.datei}: {h}" for h in l.hinweise]
            for p in l.personen:
                alt = bestand.get(p.schluessel)
                zeilen.append([_d(p.anreise), p.name, p.massnahme or p.gruppe, Pille("ja", "ok") if p.internat else Pille("nein", "neutral"),
                               _d((alt.abreise if alt else None) or p.abreise), "bekannt" if alt else "neu"])
        pt.fuellen(zeilen)
        pt.hoehe_anpassen(10)
        personen.inhalt.addWidget(pt)
        if hinweise:
            personen.inhalt.addWidget(label("<br>".join(hinweise[:6]), "klein", umbruch=True))
        v.addWidget(personen)
        v.addStretch()

        unten = QHBoxLayout()
        unten.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.clicked.connect(self.reject)
        n = sum(len(l.personen) for l in self._listen)
        self.ok = knopf(f"{n} Personen importieren" if n else "Importieren", "primary", "haken")
        self.ok.setEnabled(n > 0)
        self.ok.clicked.connect(self._importieren)
        unten.addWidget(abbrechen)
        unten.addWidget(self.ok)
        v.addLayout(unten)

    def _importieren(self) -> None:
        for l in self._listen:
            b = anreiseliste.importieren(l)
            self.bericht.neu += b.neu
            self.bericht.aktualisiert += b.aktualisiert
            self.bericht.entfernt += b.entfernt
        self.accept()


class UwtDialog(QDialog):
    def __init__(self, pfad: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UWT importieren")
        self.resize(820, 760)
        self.ergebnis = (0, 0)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        v.addWidget(label("UWT importieren", "seitentitel"))
        v.addWidget(label(f"{pfad.name} · Die UWT steht nicht in der Pivot – jeder Block zählt über den ganzen Zeitraum "
                          "(inkl. Wochenenden) zur Belegung Goslar. Ein Block derselben Klasse, der sich mit einem "
                          "vorhandenen überschneidet, ersetzt ihn – Personen und Zimmer aus einer PDF-Liste bleiben erhalten.",
                          "muted", umbruch=True))
        try:
            self.liste = uwt.lesen(pfad)
        except Exception as exc:
            self.liste = None
            v.addWidget(Hinweis(f"Die Datei konnte nicht gelesen werden: {exc}", "fehler"))
        if self.liste:
            bl = self.liste.bloecke
            k = Karte("Blöcke", f"{len(bl)} Blöcke · {len({b.klasse for b in bl})} Klassen · "
                                f"{bl[0].anreise:%d.%m.%Y} bis {max(b.abreise for b in bl):%d.%m.%Y}")
            t = Tabelle(["Klasse", "Anzahl", "Anreise", "Abreise", "Nächte"], ["l", "r", "l", "l", "r"], dehnen=0)
            t.fuellen([[b.klasse, b.anzahl, _d(b.anreise), _d(b.abreise), (b.abreise - b.anreise).days] for b in self.liste.bloecke])
            t.hoehe_anpassen(12)
            k.inhalt.addWidget(t)
            v.addWidget(k)
            if self.liste.personen:
                kp = Karte("Personen mit Zimmer")
                tp = Tabelle(["TN-ID", "Name", "Klasse", "Zimmer"], ["l", "l", "l", "l"], dehnen=1)
                tp.fuellen([[p.tn_id, p.name, p.klasse, p.zimmer] for p in self.liste.personen])
                tp.hoehe_anpassen(8)
                kp.inhalt.addWidget(tp)
                v.addWidget(kp)
            for h in self.liste.hinweise:
                v.addWidget(Hinweis(h, "warnung"))
        v.addStretch()
        unten = QHBoxLayout()
        unten.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.clicked.connect(self.reject)
        ok = knopf("Importieren", "primary", "haken")
        ok.setEnabled(bool(self.liste))
        ok.clicked.connect(self._importieren)
        unten.addWidget(abbrechen)
        unten.addWidget(ok)
        v.addLayout(unten)

    def _importieren(self) -> None:
        self.ergebnis = uwt.importieren(self.liste)
        self.accept()


class PersonDialog(QDialog):
    """Abreise und Erinnerung einer Person pflegen – oder eine Person von Hand anlegen."""

    def __init__(self, person: anreiseliste.Person | None = None, parent=None):
        super().__init__(parent)
        self.neu = person is None
        self.loeschen = False
        heute = date.today()
        self.person = person or anreiseliste.Person(name="", massnahme="", anreise=heute, internat=True)
        e = speicher.einstellungen().get("erinnerung", {})
        self.setWindowTitle("Person anlegen" if self.neu else self.person.name)
        self.setMinimumWidth(520)

        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(14)
        v.addWidget(label("Person anlegen" if self.neu else self.person.name, "seitentitel"))
        if not self.neu:
            if self.person.liste == anreiseliste.MANUELL:
                herkunft = "von Hand angelegt"
            else:
                tag, gruppe = self.person.liste.split("|", 1)
                herkunft = f"aus Anreiseliste {date.fromisoformat(tag):%d.%m.%Y}" + (" EMR" if gruppe == "EMR" else "")
            v.addWidget(label(f"{self.person.massnahme or self.person.gruppe} · Anreise {_d(self.person.anreise)} · {herkunft}"
                              + (f" · TN-ID {self.person.tn_id}" if self.person.tn_id else ""), "muted", umbruch=True))

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.name = QLineEdit(self.person.name)
        self.name.setPlaceholderText("Nachname, Vorname")
        self.massnahme = QLineEdit(self.person.massnahme)
        self.massnahme.setPlaceholderText("z. B. RVL, EMR ASS")
        self.anreise = DatumFeld(self.person.anreise)
        self.internat = QCheckBox("Wohnt im Internat")
        self.internat.setChecked(bool(self.person.internat))
        if self.neu:
            form.addRow("Name", self.name)
            form.addRow("Maßnahme", self.massnahme)
            form.addRow("Anreise", self.anreise)
            form.addRow("", self.internat)

        angaben = QHBoxLayout()
        self.geschlecht = QComboBox()
        for wert, text in (("", "unbekannt"), ("m", "männlich"), ("w", "weiblich"), ("d", "divers")):
            self.geschlecht.addItem(text, wert)
        self.geschlecht.setCurrentIndex(max(0, self.geschlecht.findData(self.person.geschlecht)))
        if not self.person.geschlecht and self.person.name:
            from ..zimmerplan import geschlecht_raten

            geraten = geschlecht_raten(self.person.name)
            self.geschlecht.setItemText(0, f"unbekannt (geschätzt: {'männlich' if geraten == 'm' else 'weiblich'})")
        self.tier = QCheckBox("kommt mit Tier")
        self.tier.setChecked(self.person.tier)
        angaben.addWidget(self.geschlecht)
        angaben.addWidget(self.tier)
        angaben.addStretch()
        form.addRow("Geschlecht", angaben)
        self.bemerkung = QLineEdit(self.person.bemerkung)
        self.bemerkung.setPlaceholderText("z. B. Hund, barrierefrei, kommt einen Tag später …")
        form.addRow("Bemerkung", self.bemerkung)

        abreise_zeile = QHBoxLayout()
        self.abreise = DatumFeld(self.person.abreise or max(self.person.anreise, heute) + timedelta(days=28))
        self.offen = QCheckBox("noch offen")
        self.offen.setChecked(self.person.abreise is None)
        self.offen.toggled.connect(self._aktualisieren)
        abreise_zeile.addWidget(self.abreise)
        abreise_zeile.addWidget(self.offen)
        abreise_zeile.addStretch()
        form.addRow("Abreise", abreise_zeile)

        self.erinnern = QCheckBox("Erinnerung an die Abreise")
        self.erinnern.setChecked(self.person.erinnerung_tage is not None or (self.person.abreise is None and e.get("immer", True)))
        self.erinnern.toggled.connect(self._aktualisieren)
        form.addRow("", self.erinnern)
        erin = QHBoxLayout()
        self.tage = QSpinBox()
        self.tage.setRange(0, 60)
        self.tage.setSuffix(" Tage vorher")
        self.tage.setSpecialValueText("am Abreisetag")
        self.tage.setValue(self.person.erinnerung_tage if self.person.erinnerung_tage is not None else int(e.get("tage", 2)))
        self.kanal = QComboBox()
        for k, text in erinnerung.KANAELE.items():
            self.kanal.addItem(text, k)
            if k in ("outlook", "mail") and not erinnerung.outlook_moeglich():
                self.kanal.model().item(self.kanal.count() - 1).setEnabled(False)
        kanal = self.person.erinnerung_kanal or e.get("kanal") or erinnerung.standard_kanal()
        if kanal in ("outlook", "mail") and not erinnerung.outlook_moeglich():
            kanal = "app"
        self.kanal.setCurrentIndex(max(0, self.kanal.findData(kanal)))
        erin.addWidget(self.tage)
        erin.addWidget(self.kanal, 1)
        form.addRow("", erin)
        v.addLayout(form)
        self.info = label("", "klein", umbruch=True)
        v.addWidget(self.info)

        unten = QHBoxLayout()
        if not self.neu:
            weg = knopf("Person entfernen", "gefahr", "loeschen")
            weg.clicked.connect(self._loeschen)
            unten.addWidget(weg)
        unten.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.clicked.connect(self.reject)
        ok = knopf("Speichern", "primary", "haken")
        ok.clicked.connect(self._speichern)
        unten.addWidget(abbrechen)
        unten.addWidget(ok)
        v.addLayout(unten)
        for w in (self.tage,):
            w.valueChanged.connect(self._aktualisieren)
        self.abreise.geaendert.connect(self._aktualisieren)
        self.kanal.currentIndexChanged.connect(self._aktualisieren)
        self._aktualisieren()

    def _aktualisieren(self, *_):
        offen = self.offen.isChecked()
        self.abreise.setEnabled(not offen)
        self.erinnern.setEnabled(not offen)
        aktiv = self.erinnern.isChecked() and not offen
        self.tage.setEnabled(aktiv)
        self.kanal.setEnabled(aktiv)
        if offen:
            self.info.setText("Ohne Abreise zählt die Person nur als Anreise-Termin (oder mit der Standarddauer aus "
                              "Daten → Anreisen).")
        elif aktiv:
            am = self.abreise.datum() - timedelta(days=self.tage.value())
            wie = {"outlook": "als Termin in Ihrem Outlook-Kalender (Erinnerung um 8 Uhr)",
                   "mail": "per E-Mail an Sie, von Outlook am Erinnerungstag um 8 Uhr verschickt",
                   "ics": "über eine Kalenderdatei, die sich zum Import in den Kalender öffnet",
                   "app": "beim Start des Dashboards und auf der Übersicht"}[self.kanal.currentData()]
            self.info.setText(f"Erinnerung am <b>{am:%d.%m.%Y}</b> {wie}.")
        else:
            self.info.setText("")

    def _speichern(self) -> None:
        p = anreiseliste.Person(**{k: getattr(self.person, k) for k in self.person.__dataclass_fields__})
        if self.neu:
            if not self.name.text().strip():
                self.info.setText("<b>Bitte einen Namen eintragen.</b>")
                return
            p.name, p.massnahme = self.name.text().strip(), self.massnahme.text().strip()
            p.anreise, p.internat = self.anreise.datum(), self.internat.isChecked()
        p.geschlecht, p.tier, p.bemerkung = self.geschlecht.currentData(), self.tier.isChecked(), self.bemerkung.text().strip()
        p.abreise = None if self.offen.isChecked() else self.abreise.datum()
        if p.abreise and p.abreise < p.anreise:
            self.info.setText("<b>Die Abreise liegt vor der Anreise.</b>")
            return
        if p.abreise and self.erinnern.isChecked():
            p.erinnerung_tage, p.erinnerung_kanal = self.tage.value(), self.kanal.currentData()
        else:
            p.erinnerung_tage, p.erinnerung_kanal = None, ""
        if (p.abreise, p.erinnerung_tage) != (self.person.abreise, self.person.erinnerung_tage):
            p.erledigt = False
        self.ergebnis = p
        self.accept()

    def _loeschen(self) -> None:
        if QMessageBox.question(self, "Person entfernen", f"{self.person.name} aus den Anreisen entfernen?") == QMessageBox.Yes:
            self.loeschen = True
            self.ergebnis = None
            self.accept()


def erinnerung_abgleichen(alt: anreiseliste.Person | None, neu: anreiseliste.Person | None) -> tuple[str, str] | None:
    """Outlook-Termin/Mail bzw. .ics an den neuen Stand anpassen (läuft im GUI-Thread).
    Setzt ``neu.erinnerung_id``. Gibt (Meldung, Art) zurück, wenn es etwas zu melden gibt."""
    def schluessel(p):
        return None if p is None else (p.abreise, p.erinnerung_tage, p.erinnerung_kanal, p.name)

    if schluessel(alt) == schluessel(neu):
        if neu is not None and alt is not None:
            neu.erinnerung_id = alt.erinnerung_id
        return None
    if alt is not None and alt.erinnerung_id and alt.erinnerung_kanal in ("outlook", "mail"):
        erinnerung.outlook_entfernen(alt.erinnerung_id)
    if neu is None or neu.erinnerung_tage is None or neu.abreise is None:
        if neu is not None:
            neu.erinnerung_id = ""
        return None
    titel = erinnerung.betreff(neu.name, neu.abreise)
    text = (f"{neu.name} ({neu.massnahme or neu.gruppe}) reist am {neu.abreise:%d.%m.%Y} ab "
            f"(Anreise {neu.anreise:%d.%m.%Y}, Internat Goslar).\n\nEingetragen im Belegungsdashboard.")
    am = neu.erinnerung_am
    try:
        if neu.erinnerung_kanal == "outlook":
            neu.erinnerung_id = erinnerung.outlook_termin(titel, neu.abreise, neu.erinnerung_tage, text)
            return f"Outlook-Termin am {neu.abreise:%d.%m.%Y} angelegt, Erinnerung am {am:%d.%m.%Y}.", "ok"
        if neu.erinnerung_kanal == "mail":
            empfaenger = speicher.einstellungen().get("erinnerung", {}).get("empfaenger", "")
            neu.erinnerung_id = erinnerung.outlook_mail(titel, am, text, empfaenger)
            return f"Erinnerungs-Mail wird am {am:%d.%m.%Y} um 8 Uhr verschickt.", "ok"
        if neu.erinnerung_kanal == "ics":
            pfad = erinnerung.ics_speichern(titel, neu.abreise, neu.erinnerung_tage, text, f"abreise_{neu.schluessel}")
            erinnerung.ics_oeffnen(pfad)
            neu.erinnerung_id = ""
            return f"Kalenderdatei erstellt: {pfad.name}", "ok"
    except Exception as exc:
        neu.erinnerung_kanal, neu.erinnerung_id = "app", ""
        return (f"Outlook nicht erreichbar ({exc}) – die Erinnerung erscheint stattdessen im Dashboard.", "warnung")
    neu.erinnerung_id = ""
    return f"Erinnerung am {am:%d.%m.%Y} im Dashboard.", "ok"
