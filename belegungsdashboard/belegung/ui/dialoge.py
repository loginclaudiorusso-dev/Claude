"""Dialoge: Listen-Import, Anreiselisten, UWT, Abreise/Erinnerung und Pivot-Struktur."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout,
)
from openpyxl.utils import get_column_letter

from .. import anreiseliste, einheitsliste, erinnerung, importe, pivot, speicher, termine, uwt
from ..konfig import STANDORT_LABEL, STANDORTE
from . import theme
from .basis import Worker
from .widgets import DatumFeld, Hinweis, Karte, Pille, Tabelle, knopf, label, leeren


def scrollbar_machen(dialog: QDialog, breite: int, hoehe: int) -> None:
    """Inhalt eines Dialogs scrollbar machen; die Knopfleiste (letzter Eintrag) bleibt immer sichtbar.
    Die Größe wird auf den Bildschirm begrenzt – auch bei vielen Einträgen oder Windows-Skalierung."""
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QFrame, QScrollArea, QWidget

    v = dialog.layout()
    unten = v.takeAt(v.count() - 1)
    inhalt = QWidget()
    inhalt.setObjectName("seiteninhalt")
    iv = QVBoxLayout(inhalt)
    iv.setContentsMargins(0, 0, 10, 0)
    iv.setSpacing(v.spacing())
    while v.count():
        item = v.takeAt(0)
        if item.widget() is not None:
            iv.addWidget(item.widget())
        elif item.layout() is not None:
            lay = item.layout()
            lay.setParent(None)
            iv.addLayout(lay)
        else:
            iv.addItem(item)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(inhalt)
    v.addWidget(scroll, 1)
    if unten is not None and unten.layout() is not None:
        lay = unten.layout()
        lay.setParent(None)
        v.addLayout(lay)
    bildschirm = (dialog.screen() or QGuiApplication.primaryScreen()).availableGeometry()
    # mindestens so breit wie der Inhalt (sonst würde rechts etwas abgeschnitten), höchstens Bildschirm
    breite = max(breite, inhalt.minimumSizeHint().width() + scroll.verticalScrollBar().sizeHint().width() + 60)
    dialog.resize(min(breite, int(bildschirm.width() * 0.94)), min(hoehe, int(bildschirm.height() * 0.9)))


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
        scrollbar_machen(self, 980, 720)

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
        scrollbar_machen(self, 980, 720)

    def _kopf_wechsel(self, wert: int) -> None:
        self.zuordnung.kopfzeile = wert - 1
        kopf = self.tabelle.zeilen[wert - 1]
        neu = importe.zuordnung_erraten(importe.Tabelle(self.pfad, [], None, [kopf]))
        self.zuordnung.spalten = neu.spalten
        self._spalten_fuellen()
        self._vorschau()
        scrollbar_machen(self, 980, 720)

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
        self._einheit: list = []                 # Einheitslisten: UWT-Teil wird mit übernommen
        fehler, einheit_hinweise = [], []
        for p in pfade:
            try:
                if einheitsliste.ist_einheitsliste(p):
                    erg = einheitsliste.lesen(p)
                    self._listen += erg.anreisen
                    self._einheit.append(erg)
                    einheit_hinweise += [f"<b>{p.name}</b>: {h}" for h in erg.hinweise]
                    if erg.uwt is not None:
                        einheit_hinweise.append(f"<b>{p.name}</b>: UWT – {len(erg.uwt.bloecke)} Blöcke mit "
                                                f"{len(erg.uwt.personen)} Personen werden mit übernommen"
                                                + (f" (DZ-Partner für {', '.join(erg.klassen)})" if erg.klassen else "") + ".")
                else:
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
        for h in einheit_hinweise:
            v.addWidget(Hinweis(h, "warnung" if "ohne Abreise" in h else "info"))

        bestand = {p.schluessel: p for p in anreiseliste.laden()[0]}
        listen = Karte("Listen")
        lt = Tabelle(["Datei", "Anreise", "Gruppe", "Personen", "mit Internat", "Status"], ["l", "l", "l", "r", "r", "l"], dehnen=0)
        lt.fuellen([[l.datei, _d(l.datum), l.gruppe, len(l.personen), l.mit_internat,
                     "bereits importiert – wird aktualisiert" if any(p.liste == l.schluessel for p in bestand.values()) else "neu"]
                    for l in self._listen])
        lt.hoehe_anpassen(6)
        listen.inhalt.addWidget(lt)
        v.addWidget(listen)

        personen = Karte("Personen", "Gruppe, Geschlecht und Tier bestimmen die Zimmerwahl – bitte prüfen, wo etwas "
                                     "nicht eindeutig ist (gelb).")
        from .. import zimmerplan as zp

        angaben = zp.angaben_laden()
        self._zeilen: list[tuple] = []          # (Person, Gruppe-Combo, erkannt, m/w-Combo, geschätzt, Tier-Box)
        pt = Tabelle(["Anreise", "Name", "Maßnahme", "Gruppe", "m/w", "Tier", "Internat", ""],
                     ["l", "l", "l", "l", "l", "l", "l", "l"], dehnen=1)
        pt.verticalHeader().setDefaultSectionSize(42)
        zeilen, hinweise, farben = [], [], {}
        t = theme.T
        offen = 0
        for l in self._listen:
            hinweise += [f"{l.datei}: {h}" for h in l.hinweise]
            for p in l.personen:
                alt = bestand.get(p.schluessel)
                a = angaben.get(p.schluessel, {})
                erkannt = zp.gruppe_von(p.massnahme, "EMR" if p.gruppe == "EMR" else "")
                gruppe = QComboBox()
                if not erkannt and not a.get("gruppe"):
                    gruppe.addItem("— bitte wählen —", "")
                for g in ("EMR", "ASS", "RVL", "RVT", "Reha"):
                    gruppe.addItem(zp.GRUPPE_LABEL[g], g)
                gruppe.setCurrentIndex(max(0, gruppe.findData(a.get("gruppe") or erkannt or "")))
                gruppe.setMinimumWidth(150)
                geschaetzt = p.geschlecht or zp.geschlecht_raten(p.name)
                mw = QComboBox()
                for wert, text in (("m", "m"), ("w", "w"), ("d", "d"), ("", "?")):
                    mw.addItem(text + ("*" if wert == geschaetzt and not p.geschlecht and not a.get("geschlecht") else ""), wert)
                mw.setCurrentIndex(max(0, mw.findData(a.get("geschlecht") or p.geschlecht or geschaetzt)))
                mw.setToolTip("* aus dem Vornamen geschätzt")
                mw.setMinimumWidth(66)
                tier = QCheckBox()
                tier.setChecked(bool(a.get("tier", p.tier)))
                if p.bemerkung:
                    tier.setToolTip(p.bemerkung)
                unklar = p.internat and not erkannt and not a.get("gruppe")
                offen += bool(unklar)
                self._zeilen.append((p, gruppe, erkannt, mw, geschaetzt, tier))
                r = len(zeilen)
                zeilen.append([_d(p.anreise), p.name + (" · " + p.bemerkung if p.bemerkung else ""), p.massnahme or "–",
                               self._zelle(gruppe), self._zelle(mw), self._zelle(tier, 14),
                               Pille("ja", "ok") if p.internat else Pille("nein", "neutral"), "bekannt" if alt else "neu"])
                if unklar:
                    farben[(r, 2)] = t.knapp
        pt.fuellen(zeilen, farben)
        for r, (p, *_rest) in enumerate(self._zeilen):
            if p.bemerkung and pt.item(r, 1):
                pt.item(r, 1).setToolTip(p.bemerkung)
        pt.widgets_einpassen()
        pt.hoehe_anpassen(12)
        if offen:
            alle = QHBoxLayout()
            alle.addWidget(Hinweis(f"Bei {offen} Person{'en' if offen > 1 else ''} ist die Maßnahme nicht erkennbar – "
                                   "bitte die Gruppe wählen (wichtig für Haus und Etage).", "warnung"), 1)
            setzen = QComboBox()
            setzen.addItem("Für alle offenen setzen …", "")
            for g in ("EMR", "ASS", "RVL", "RVT", "Reha"):
                setzen.addItem(zp.GRUPPE_LABEL[g], g)
            setzen.currentIndexChanged.connect(lambda _i: self._alle_setzen(setzen.currentData()))
            alle.addWidget(setzen)
            personen.inhalt.addLayout(alle)
        personen.inhalt.addWidget(pt)
        if hinweise:
            personen.inhalt.addWidget(label("<br>".join(hinweise[:6]), "klein", umbruch=True))
        v.addWidget(personen)
        v.addStretch()

        unten = QHBoxLayout()
        unten.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.clicked.connect(self.reject)
        n = sum(len(l.personen) for l in self._listen) + sum(len(e.uwt.personen) for e in self._einheit if e.uwt)
        self.ok = knopf(f"{n} Personen importieren" if n else "Importieren", "primary", "haken")
        self.ok.setEnabled(n > 0)
        self.ok.clicked.connect(self._importieren)
        unten.addWidget(abbrechen)
        unten.addWidget(self.ok)
        v.addLayout(unten)
        self.anreisetage: list[date] = []
        scrollbar_machen(self, 1080, 820)

    @staticmethod
    def _zelle(w, links: int = 4):
        from PySide6.QtWidgets import QWidget

        h = QWidget()
        lay = QHBoxLayout(h)
        lay.setContentsMargins(links, 0, 4, 0)
        lay.addWidget(w, 0, Qt.AlignVCenter)
        lay.addStretch()
        return h

    def _alle_setzen(self, gruppe: str) -> None:
        if not gruppe:
            return
        for p, combo, erkannt, *_ in self._zeilen:
            if not erkannt and combo.currentData() == "":
                combo.setCurrentIndex(combo.findData(gruppe))

    def _importieren(self) -> None:
        from .. import zimmerplan as zp

        for l in self._listen:
            b = anreiseliste.importieren(l)
            self.bericht.neu += b.neu
            self.bericht.aktualisiert += b.aktualisiert
            self.bericht.entfernt += b.entfernt
        for e in self._einheit:
            if e.uwt is not None:
                einheitsliste.importieren(einheitsliste.Ergebnis(uwt=e.uwt, klassen=e.klassen))
        for p, gruppe, erkannt, mw, geschaetzt, tier in self._zeilen:
            werte = {}
            if gruppe.currentData() and gruppe.currentData() != erkannt:
                werte["gruppe"] = gruppe.currentData()
            if mw.currentData() != (p.geschlecht or geschaetzt):
                werte["geschlecht"] = mw.currentData()
            if tier.isChecked() != p.tier:
                werte["tier"] = tier.isChecked()
            if werte:
                zp.angabe_setzen(p.schluessel, **werte)
        self.anreisetage = sorted({p.anreise for l in self._listen for p in l.personen if p.internat})
        self.accept()


class UwtDialog(QDialog):
    """UWT importieren: Anreisekalender (Excel), Blockbeschulungsplan (PDF) oder An-/Abreiseliste (PDF)."""

    def __init__(self, pfad: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UWT importieren")
        self.ergebnis = (0, 0)
        self._spins: dict[str, QSpinBox] = {}
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
            klassen = sorted({b.klasse for b in self.liste.bloecke})
            if not self.liste.personen and pfad.suffix.lower() == ".pdf":
                # Blockplan: Anzahl je Klasse kommt aus den Klassenstärken (UWTler im Internat)
                staerken = uwt.klassenstaerken()
                kk = Karte("Klassenstärken im Internat", "Wie viele Schüler/-innen je Klasse im Internat wohnen – "
                                                         "0 = Klasse zählt nicht (z. B. Chemikanten). Wird gespeichert.")
                gitter = QGridLayout()
                gitter.setHorizontalSpacing(18)
                gitter.setVerticalSpacing(8)
                for i, k in enumerate(klassen):
                    sp = QSpinBox()
                    sp.setRange(0, 60)
                    sp.setValue(int(staerken.get(k, 0)))
                    sp.setMinimumWidth(70)
                    sp.valueChanged.connect(self._bloecke_zeigen)
                    self._spins[k] = sp
                    gitter.addWidget(label(k, "fett"), i // 4 * 2, i % 4)
                    gitter.addWidget(sp, i // 4 * 2 + 1, i % 4)
                kk.inhalt.addLayout(gitter)
                v.addWidget(kk)
            self.bloecke_karte = Karte("Blöcke", "")
            self.bloecke_tab = Tabelle(["Klasse", "Anzahl", "Anreise", "Abreise", "Nächte"], ["l", "r", "l", "l", "r"], dehnen=0)
            self.bloecke_karte.inhalt.addWidget(self.bloecke_tab)
            v.addWidget(self.bloecke_karte)
            if self.liste.personen:
                kp = Karte("Personen mit Zimmer")
                tp = Tabelle(["TN-ID", "Name", "Klasse", "Zimmer"], ["l", "l", "l", "l"], dehnen=1)
                tp.fuellen([[p.tn_id, p.name, p.klasse, p.zimmer] for p in self.liste.personen])
                tp.hoehe_anpassen(8)
                kp.inhalt.addWidget(tp)
                v.addWidget(kp)
            for h in self.liste.hinweise:
                v.addWidget(Hinweis(h, "info"))
            self._bloecke_zeigen()
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
        scrollbar_machen(self, 900, 820)

    def _bloecke_zeigen(self, *_):
        for b in self.liste.bloecke:
            if b.klasse in self._spins:
                b.anzahl = self._spins[b.klasse].value()
        bl = self.liste.bloecke
        zaehlen = [b for b in bl if b.anzahl > 0]
        self.bloecke_karte.untertitel(f"{len(zaehlen)} Blöcke · {len({b.klasse for b in zaehlen})} Klassen · "
                                      f"{bl[0].anreise:%d.%m.%Y} bis {max(b.abreise for b in bl):%d.%m.%Y}"
                                      + (f" · {len(bl) - len(zaehlen)} ohne Internat" if len(zaehlen) < len(bl) else ""))
        farben = {}
        zeilen = []
        for r, b in enumerate(bl):
            zeilen.append([b.klasse, b.anzahl, _d(b.anreise), _d(b.abreise), (b.abreise - b.anreise).days])
            if b.anzahl <= 0:
                for c in range(5):
                    farben[(r, c)] = theme.T.text_3
        self.bloecke_tab.fuellen(zeilen, farben)
        self.bloecke_tab.hoehe_anpassen(12)

    def _importieren(self) -> None:
        if self._spins:
            uwt.klassenstaerken_speichern({k: sp.value() for k, sp in self._spins.items()})
        self.ergebnis = uwt.importieren(self.liste)
        self.accept()


class PersonDialog(QDialog):
    """Abreise und Erinnerung einer Person pflegen – oder eine Person von Hand anlegen."""

    def __init__(self, person: anreiseliste.Person | None = None, parent=None, anreise: date | None = None):
        super().__init__(parent)
        self.neu = person is None
        self.loeschen = False
        heute = date.today()
        self.person = person or anreiseliste.Person(name="", massnahme="", anreise=anreise or heute, internat=True)
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
        from .. import zimmerplan as zp

        self.gruppe = QComboBox()
        gespeichert = zp.angaben_laden().get(self.person.schluessel, {}).get("gruppe") if not self.neu else None
        self._gruppe_erkannt = zp.gruppe_von(self.person.massnahme, "EMR" if self.person.gruppe == "EMR" else "")
        for g in ("EMR", "ASS", "RVL", "RVT", "Reha"):
            self.gruppe.addItem(zp.GRUPPE_LABEL[g], g)
        self.gruppe.setCurrentIndex(max(0, self.gruppe.findData(gespeichert or self._gruppe_erkannt or "Reha")))
        self.gruppe.setToolTip("Bestimmt Haus und Etage im Zimmerplan (z. B. EMR nur Haus 2, Etage 1–2)")
        form.addRow("Gruppe", self.gruppe)
        self.bemerkung = QLineEdit(self.person.bemerkung)
        self.bemerkung.setPlaceholderText("z. B. Hund, barrierefrei, kommt einen Tag später …")
        self.bemerkung.setToolTip("Notizen zur Anreise erscheinen als Erinnerung im Terminkalender (Seite Termine)")
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
        scrollbar_machen(self, 620, 720)

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
                   "app": "im Terminkalender des Dashboards (Seite Termine, mit Windows-Benachrichtigung)"}[self.kanal.currentData()]
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
        if p.abreise != self.person.abreise and (not self.neu or p.abreise is not None):
            p.abreise_quelle = "hand"      # von Hand geändert – die automatische EMR-Abreise greift nicht mehr
        if p.abreise and p.abreise < p.anreise:
            self.info.setText("<b>Die Abreise liegt vor der Anreise.</b>")
            return
        if p.abreise and self.erinnern.isChecked():
            p.erinnerung_tage, p.erinnerung_kanal = self.tage.value(), self.kanal.currentData()
        else:
            p.erinnerung_tage, p.erinnerung_kanal = None, ""
        if (p.abreise, p.erinnerung_tage) != (self.person.abreise, self.person.erinnerung_tage):
            p.erledigt = False
        from .. import zimmerplan as zp

        if self.gruppe.currentData() != self._gruppe_erkannt or not self.neu:
            zp.angabe_setzen(p.schluessel, gruppe=self.gruppe.currentData())
        if p.gruppe != "EMR" and self.gruppe.currentData() == "EMR":
            p.gruppe = "EMR"
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


class TerminDialog(QDialog):
    """Eigenen Termin mit Erinnerung anlegen oder ändern."""

    def __init__(self, termin=None, parent=None, datum: date | None = None):
        from PySide6.QtWidgets import QPlainTextEdit

        super().__init__(parent)
        self.termin = termin
        self.ergebnis = None
        self.loeschen = False
        self.setWindowTitle("Termin" if termin is None else termin.titel)
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.datum = DatumFeld(termin.datum if termin else (datum or date.today()))
        form.addRow("Datum", self.datum)
        self.titel = QLineEdit(termin.titel if termin else "")
        self.titel.setPlaceholderText("z. B. Duschstuhl für Herrn M. bereitstellen")
        form.addRow("Was", self.titel)
        self.text = QPlainTextEdit(termin.text if termin else "")
        self.text.setPlaceholderText("Notiz (optional)")
        self.text.setFixedHeight(90)
        form.addRow("Notiz", self.text)
        self.vorlauf = QSpinBox()
        self.vorlauf.setRange(-1, 90)
        self.vorlauf.setSpecialValueText("keine Erinnerung")
        self.vorlauf.setSuffix(" Tage vorher")
        self.vorlauf.setValue(termin.vorlauf if termin else 1)
        self.vorlauf.setFixedWidth(200)
        form.addRow("Erinnern", self.vorlauf)
        v.addLayout(form)
        self.info = label("", "klein", umbruch=True)
        v.addWidget(self.info)
        unten = QHBoxLayout()
        if termin is not None:
            weg = knopf("Löschen", "gefahr", "loeschen")
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
        self.vorlauf.valueChanged.connect(self._info)
        self.datum.geaendert.connect(self._info)
        self._info()
        scrollbar_machen(self, 520, 480)

    def _info(self, *_):
        if self.vorlauf.value() < 0:
            self.info.setText("Steht nur im Kalender, ohne Erinnerung.")
            return
        am = self.datum.datum() - timedelta(days=self.vorlauf.value())
        self.info.setText(f"Erinnerung ab <b>{am:%d.%m.%Y}</b> – jeden Tag, bis der Termin als erledigt abgehakt ist.")

    def _loeschen(self):
        self.loeschen = True
        self.accept()

    def _speichern(self):
        if not self.titel.text().strip():
            self.info.setText("<b>Bitte eintragen, worum es geht.</b>")
            return
        self.ergebnis = termine.Termin(self.termin.id if self.termin else "", self.datum.datum(), self.titel.text().strip(),
                                            self.text.toPlainText().strip(), "eigen", vorlauf=self.vorlauf.value())
        self.accept()
