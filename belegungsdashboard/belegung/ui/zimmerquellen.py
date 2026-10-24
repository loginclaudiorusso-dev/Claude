"""Importe der Zimmerplanung (Gebäudeplan, Zimmer-Pivot, ZKL), die Planungs-Einstellungen und der Änderungsverlauf.

Bis 6.13 lag das alles im Zimmerplan-Reiter „Quellen“, zusätzlich zur Seite „Daten & Import“. Seit 6.14 gibt es einen
Ort für alle Importe (Daten & Import → „Gebäudeplan & ZKL“), die Planungs-Einstellungen stehen unter Einstellungen,
der Verlauf öffnet sich aus dem Zimmerplan („Verlauf“). Die Import-Funktionen sind hier als Funktionen abgelegt,
damit Hinweise (z. B. „Gebäudeplan ist alt“) direkt importieren können, ohne die Seite zu wechseln.
"""

from __future__ import annotations

import shutil
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QSpinBox, QVBoxLayout, QWidget,
)

from .. import gebaeudeplan, speicher
from .. import zimmerplan as zp
from .basis import Worker
from .widgets import Karte, Tabelle, knopf, label


def _gespeichert(zustand) -> None:
    zustand.zimmer_geaendert.emit()


# ---------------------------------------------------------------------------------------
# Importe als Funktionen (auch aus Hinweisen aufrufbar)
# ---------------------------------------------------------------------------------------

def plan_importieren(parent, zustand) -> bool:
    start = speicher.einstellungen().get("import_ordner_gebaeudeplan") or str(Path.home())
    pfad, _ = QFileDialog.getOpenFileName(parent, "Gebäudeplan wählen", start, "Word (*.docx);;Alle Dateien (*)")
    if not pfad:
        return False
    speicher.einstellung_setzen("import_ordner_gebaeudeplan", str(Path(pfad).parent))
    try:
        plan = gebaeudeplan.lesen(Path(pfad))
    except Exception as exc:              # noqa: BLE001
        zustand.meldung.emit(f"Gebäudeplan konnte nicht gelesen werden: {exc}", "fehler")
        return False
    from .planabgleich_dialog import plan_pruefen, plan_uebernehmen

    # erst prüfen (Unterschiede zu Belegung und Planung, Vorrang wählen), dann übernehmen
    unterschiede = plan_pruefen(parent, zustand, plan)
    if unterschiede is None:
        return False
    kennung = None
    try:      # Kopie in den Eingangsordner – dann gilt diese Datei als aktueller Stand
        ziel = gebaeudeplan.eingangsordner() / Path(pfad).name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        if ziel.resolve() != Path(pfad).resolve():
            shutil.copy2(pfad, ziel)
        kennung = {"pfad": ziel.name, "geaendert": int(ziel.stat().st_mtime)}
    except OSError:
        pass
    plan_uebernehmen(zustand, plan, unterschiede, kennung)
    return True


def plan_einfuegen(parent, zustand) -> bool:
    mime = QApplication.clipboard().mimeData()
    text = mime.text() if mime and mime.hasText() else ""
    html = mime.html() if mime and mime.hasHtml() else ""
    try:
        plan = gebaeudeplan.aus_zwischenablage(text, html)
    except ValueError as exc:
        zustand.meldung.emit(str(exc), "fehler")
        return False
    from .planabgleich_dialog import plan_pruefen, plan_uebernehmen

    unterschiede = plan_pruefen(parent, zustand, plan)
    if unterschiede is None:
        return False
    plan_uebernehmen(zustand, plan, unterschiede, {"pfad": "Zwischenablage", "geaendert": 0})
    speicher.schreiben(f"{speicher.IMPORT_ORDNER}/gebaeudeplan_eingefuegt.json",
                       {"text": text, "html": html[:2_000_000]})       # Rohdaten zur Nachkontrolle
    return True


def eingang_oeffnen() -> None:
    ordner = gebaeudeplan.eingangsordner()
    ordner.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(ordner)))


def zkl_abgleich(parent, zustand) -> None:
    from .zkl_dialog import ZklAbgleichDialog

    if ZklAbgleichDialog(zustand, parent).exec():
        _gespeichert(zustand)


# ---------------------------------------------------------------------------------------
# Karten „Gebäudeplan & ZKL“ (Daten & Import)
# ---------------------------------------------------------------------------------------

class ZimmerQuellen(QWidget):
    """Gebäudeplan, Zimmer-Pivot und ZKL: Stand ansehen und importieren."""

    def __init__(self, zustand, parent=None):
        super().__init__(parent)
        self.z = zustand
        self.stand: zp.Planstand | None = None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        self.plan_karte = Karte("Gebäudeplan", "Word-Export aus dem Belegungssystem – Grundlage für Zimmer und Belegung")
        self.plan_text = label("", "muted", umbruch=True)
        self.plan_karte.inhalt.addWidget(self.plan_text)
        knoepfe = QHBoxLayout()
        knoepfe.setSpacing(8)
        imp = knopf("Gebäudeplan importieren", "primary", "hochladen")
        imp.clicked.connect(lambda: plan_importieren(self, self.z))
        knoepfe.addWidget(imp)
        einf = knopf("Aus Zwischenablage einfügen", "ghost", "kopieren")
        einf.setToolTip("Im Belegungssystem die Gebäudeansicht markieren (Strg+A) und kopieren (Strg+C) – dann hier klicken")
        einf.clicked.connect(lambda: plan_einfuegen(self, self.z))
        knoepfe.addWidget(einf)
        ordner = knopf("Ordner öffnen", "ghost", "datei")
        ordner.setToolTip("Gebäudepläne (.docx), die hier liegen, werden beim Öffnen des Zimmerplans automatisch übernommen")
        ordner.clicked.connect(eingang_oeffnen)
        knoepfe.addWidget(ordner)
        knoepfe.addStretch()
        self.plan_karte.inhalt.addLayout(knoepfe)
        v.addWidget(self.plan_karte)
        self.zkl_karte = Karte("Zimmerkontrollliste (ZKL)", "Excel des Internatsdienstes – ergänzt Tier, TN-Nummer und "
                                                           "Zimmer-Infos; Abweichungen zum Entscheiden")
        self.zkl_text = label("", "muted", umbruch=True)
        self.zkl_karte.inhalt.addWidget(self.zkl_text)
        kn = QHBoxLayout()
        kn.setSpacing(8)
        self.b_zkl = knopf("ZKL importieren", "primary", "tabelle")
        self.b_zkl.clicked.connect(self._zkl_importieren)
        kn.addWidget(self.b_zkl)
        self.b_zkl_abgleich = knopf("Abgleich anzeigen", "ghost")
        self.b_zkl_abgleich.clicked.connect(lambda: zkl_abgleich(self, self.z))
        kn.addWidget(self.b_zkl_abgleich)
        kn.addStretch()
        self.zkl_karte.inhalt.addLayout(kn)
        v.addWidget(self.zkl_karte)
        self.pivot_karte = Karte("Zimmer-Pivot (optional)", "Belegung je Zimmer und Tag (Rios) – ergänzt Buchungen, die "
                                                            "im Plan fehlen")
        self.pivot_text = label("", "muted", umbruch=True)
        self.pivot_karte.inhalt.addWidget(self.pivot_text)
        self.b_pivot = knopf("Zimmer-Pivot importieren", "ghost", "tabelle")
        self.b_pivot.clicked.connect(self._pivot_importieren)
        self.pivot_karte.inhalt.addWidget(self.b_pivot, 0, Qt.AlignLeft)
        v.addWidget(self.pivot_karte)
        zustand.zimmer_geaendert.connect(self._von_aussen)

    def _von_aussen(self) -> None:
        if self.isVisible():
            self.aktualisieren()
        else:
            self.stand = None                   # beim nächsten Zeigen neu

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if self.stand is None:
            self.aktualisieren()

    def aktualisieren(self) -> None:
        st = self.stand = zp.laden()
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
        if st.plan is not None:                 # Datenqualität: Belegungen ohne Namen im Export
            ohne = [b for b in st.plan.belegungen if b.art == "belegt" and zp.name_fehlt(b.name) and b.bis >= heute]
            if ohne:
                beispiele = ", ".join(sorted({b.zimmer.removeprefix("GS-") for b in ohne})[:6])
                self.plan_text.setText(self.plan_text.text() + f"<br><b>{len(ohne)} Belegung(en) ohne Namen</b> "
                                       f"(Platzhalter wie „{ohne[0].name or 'leer'}“) – Zimmer {beispiele}"
                                       + (" …" if len({b.zimmer for b in ohne}) > 6 else "")
                                       + ". Angezeigt als „Name nicht verfügbar“; bitte im Belegungssystem prüfen.")
        self._zkl_zeigen()
        zpv = st.zimmer_pivot
        if zpv is None:
            self.pivot_text.setText("Noch nicht importiert. Ergänzt gebuchte Tage, die im Gebäudeplan fehlen.")
        else:
            extra = {zid for zid, bs in st.lage.belegungen.items() for b in bs if b.name == zp.PIVOT_NAME and b.bis >= heute}
            stand = f"Stand {zpv.stand:%d.%m.%Y}" if zpv.stand else "Stand unbekannt"
            self.pivot_text.setText(f"<b>{zpv.datei}</b> · {stand}<br>{zpv.zimmer} Zimmer, {zpv.zeitraum[0]:%d.%m.%Y} – "
                                    f"{zpv.zeitraum[1]:%d.%m.%Y}<br>"
                                    + (f"<b>{len(extra)} Zimmer</b> mit Buchungen, die im Gebäudeplan fehlen – im Zeitstrahl "
                                       "lila." if extra else "Stimmt mit dem Gebäudeplan überein."))

    def _zkl_zeigen(self) -> None:
        from .. import zkl

        st, daten = self.stand, zkl.laden()
        self.b_zkl_abgleich.setEnabled(daten is not None)
        if daten is None:
            self.zkl_text.setText("Noch nicht importiert (optional). Liefert Tier (Kundengruppe „Reha-Tier“), TN-Nummern "
                                  "der Bewohner und Zimmer-Infos – und zeigt, wo ZKL und Gebäudeplan voneinander abweichen.")
            return
        offen = zkl.abgleich(st, daten)
        tier = sum(1 for bs in st.lage.belegungen.values() for b in bs if b.art == "belegt" and zkl.hat_tier(st.lage, b))
        stand = f", Daten bis {daten.stand:%d.%m.%Y}" if daten.stand else ""
        self.zkl_text.setText(f"<b>{daten.datei}</b> · Blatt „{daten.blatt}“{stand} · importiert "
                              f"{daten.importiert[:10]}<br>{len(daten.zimmer)} Zimmer, {tier} Bewohner mit Tier, "
                              f"{len(daten.uebernommen)} als belegt übernommen<br>"
                              + (f"<b>{sum(1 for p in offen if p.aktion)} offene Abweichungen</b> – „Abgleich anzeigen“."
                                 if any(p.aktion for p in offen) else "Keine offenen Abweichungen."))

    def _zkl_importieren(self) -> None:
        from .. import zkl

        start = speicher.einstellungen().get("import_ordner_zkl") or str(Path.home())
        pfad, _ = QFileDialog.getOpenFileName(self, "Zimmerkontrollliste (ZKL) wählen", start,
                                              "Excel (*.xlsx *.xlsm);;Alle Dateien (*)")
        if not pfad:
            return
        speicher.einstellung_setzen("import_ordner_zkl", str(Path(pfad).parent))
        self.b_zkl.setEnabled(False)
        self.b_zkl.setText("Wird gelesen …")

        def fertig(ergebnis) -> None:
            zkl.speichern(ergebnis)
            self.z.meldung.emit(f"ZKL importiert: {len(ergebnis.zimmer)} Zimmer aus Blatt „{ergebnis.blatt}“.", "ok")
            _gespeichert(self.z)
            zkl_abgleich(self, self.z)

        bekannt = {z.id for z in self.stand.zimmer} if self.stand else None
        self._zkl_worker = Worker(zkl.lesen, Path(pfad), bekannt, parent=self)
        self._zkl_worker.fertig.connect(fertig)
        self._zkl_worker.fehler.connect(lambda t: self.z.meldung.emit(f"ZKL konnte nicht gelesen werden: {t}", "fehler"))
        self._zkl_worker.finished.connect(lambda: (self.b_zkl.setEnabled(True), self.b_zkl.setText("ZKL importieren")))
        self._zkl_worker.start()

    def _pivot_importieren(self) -> None:
        from .. import zimmerpivot

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
            _gespeichert(self.z)

        self._pivot_worker = Worker(zimmerpivot.lesen, Path(pfad), parent=self)
        self._pivot_worker.fertig.connect(fertig)
        self._pivot_worker.fehler.connect(lambda t: self.z.meldung.emit(f"Zimmer-Pivot konnte nicht gelesen werden: {t}",
                                                                        "fehler"))
        self._pivot_worker.finished.connect(lambda: (self.b_pivot.setEnabled(True),
                                                     self.b_pivot.setText("Zimmer-Pivot importieren")))
        self._pivot_worker.start()


# ---------------------------------------------------------------------------------------
# Planungs-Einstellungen (Einstellungen)
# ---------------------------------------------------------------------------------------

class PlanungEinstellungen(Karte):
    def __init__(self, zustand, parent=None):
        super().__init__("Zimmerplanung", "Gilt für alle Vorschläge, Reinigung und Aufgaben", parent=parent)
        self.z = zustand
        f = QHBoxLayout()
        f.addWidget(label("Puffer nach jeder Abreise (Reinigung)", "klein"))
        self.puffer = QSpinBox()
        self.puffer.setRange(0, 7)
        self.puffer.setSuffix(" Tag(e)")
        self.puffer.setToolTip("0 = am Abreisetag wieder belegbar · 1 = frühestens am Tag nach der Abreise")
        self.puffer.setValue(int(speicher.einstellungen().get("zimmer_puffer", 1)))
        self.puffer.valueChanged.connect(lambda v: (speicher.einstellung_setzen("zimmer_puffer", v),
                                                    self.z.zimmer_geaendert.emit()))
        f.addWidget(self.puffer)
        f.addStretch()
        self.inhalt.addLayout(f)
        f = QHBoxLayout()
        f.addWidget(label("Facility-Check ab Aufenthalt von", "klein"))
        self.fc_monate = QSpinBox()
        self.fc_monate.setRange(1, 36)
        self.fc_monate.setSuffix(" Monaten")
        self.fc_monate.setToolTip("Nach einem Auszug nach so langer Zeit: Meldung „Elektrik prüfen, Fensterwartung“")
        self.fc_monate.setValue(int(speicher.einstellungen().get("facility_monate", 6)))
        self.fc_monate.valueChanged.connect(lambda v: (speicher.einstellung_setzen("facility_monate", v),
                                                       self.z.zimmer_geaendert.emit()))
        f.addWidget(self.fc_monate)
        f.addStretch()
        self.inhalt.addLayout(f)


# ---------------------------------------------------------------------------------------
# Verlauf (Änderungsprotokoll)
# ---------------------------------------------------------------------------------------

class VerlaufDialog(QDialog):
    """Wer wann wen in welches Zimmer geplant, umgeplant oder entfernt hat – mit „Letzte Änderung rückgängig“."""

    def __init__(self, zustand, parent=None):
        super().__init__(parent)
        self.z = zustand
        self.setWindowTitle("Verlauf der Zimmerplanung")
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Verlauf der Zimmerplanung", "seitentitel"))
        v.addWidget(label("Jede gespeicherte Änderung an Zimmern und Umzügen – neueste zuerst. Steht hier nur, was "
                          "wirklich gespeichert wurde.", "muted", umbruch=True))
        self.tab = Tabelle(["Zeit", "Aktion", "Name", "Zimmer", "Anlass", "Wer"], ["l"] * 6, dehnen=2)
        self.tab.setTextElideMode(Qt.ElideRight)
        v.addWidget(self.tab, 1)
        self.leer = label("Noch keine Änderungen gespeichert.", "muted")
        v.addWidget(self.leer)
        v.addStretch()
        unten = QHBoxLayout()
        self.b_zurueck = knopf("Letzte Änderung rückgängig", "ghost", "loeschen")
        self.b_zurueck.clicked.connect(self._rueckgaengig)
        unten.addWidget(self.b_zurueck)
        self.mehr = knopf("Ältere anzeigen", "ghost")
        self.mehr.clicked.connect(lambda: self._zeigen(self._anzahl + 200))
        unten.addWidget(self.mehr)
        unten.addStretch()
        zu = knopf("Schließen", "primary")
        zu.clicked.connect(self.accept)
        unten.addWidget(zu)
        v.addLayout(unten)
        self._anzahl = 100
        self._zeigen()
        self.resize(900, 620)

    def _zeigen(self, anzahl: int | None = None) -> None:
        from .. import aenderungen, protokoll

        self._anzahl = anzahl or self._anzahl
        alle = protokoll.laden()
        zeilen = []
        for e in alle[:self._anzahl]:
            alt, neu = e.get("alt", "").removeprefix("GS-"), e.get("neu", "").removeprefix("GS-")
            zimmer = f"{alt} → {neu}" if alt and neu and alt != neu else (neu or alt)
            zeilen.append([datetime.fromisoformat(e["zeit"]).strftime("%d.%m.%y %H:%M"), e.get("aktion", ""),
                           e.get("name", ""), zimmer, e.get("quelle", ""), e.get("wer", "")])
        self.tab.fuellen(zeilen)
        self.tab.setVisible(bool(zeilen))
        self.leer.setVisible(not zeilen)
        self.mehr.setVisible(len(alle) > self._anzahl)
        s = aenderungen.letzter()
        self.b_zurueck.setEnabled(s is not None)
        self.b_zurueck.setToolTip(f"„{s.titel}“ zurücknehmen" if s else "In dieser Sitzung wurde noch nichts geändert")

    def _rueckgaengig(self) -> None:
        from .aenderung_ui import rueckgaengig

        rueckgaengig(self, self.z)
        self._zeigen()


def verlauf_oeffnen(parent, zustand) -> None:
    VerlaufDialog(zustand, parent).exec()
