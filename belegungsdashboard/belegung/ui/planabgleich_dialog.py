"""Maske „Gebäudeplan prüfen“: vor dem Übernehmen zeigen, was im neuen Gebäudeplan anders ist als Belegung und
eigenen Einträgen im Zimmerplan – und bei Unterschieden zu eigenen Einträgen wählen, was gelten soll. Logik: ``planabgleich``."""

from __future__ import annotations

from datetime import date

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QHeaderView, QVBoxLayout

from .. import aenderungen
from .. import planabgleich as pa
from .. import zimmerplan as zp
from .widgets import Hinweis, Tabelle, knopf, label

ART_STUFE = {"konflikt": "fehler", "zimmer": "warnung", "zeitraum": "warnung", "fehlt": "warnung", "neu": "info"}


class PlanAbgleichDialog(QDialog):
    def __init__(self, zustand, neu, stand: zp.Planstand, parent=None, heute: date | None = None):
        super().__init__(parent)
        self.z, self.neu = zustand, neu
        self.unterschiede = pa.vergleichen(neu, stand, heute)
        self.setWindowTitle("Gebäudeplan prüfen")
        self.setMinimumSize(1000, 560)
        bild = QGuiApplication.primaryScreen().availableGeometry() if QGuiApplication.primaryScreen() else None
        if bild is not None:                           # so breit wie sinnvoll, ohne über den Bildschirm zu ragen
            self.resize(min(1280, bild.width() - 60), min(760, bild.height() - 60))
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Gebäudeplan prüfen, bevor er übernommen wird", "seitentitel"))
        def herkunft(plan) -> str:
            stand = f"Stand {plan.stand:%d.%m.%Y}" if plan.stand else "ohne Stand-Datum"
            return f"„{plan.datei}“, {stand}"

        belegt = sum(1 for b in neu.belegungen if b.art == "belegt")
        bisher = (f"der bisherige Gebäudeplan ({herkunft(stand.plan)})" if stand.plan is not None
                  else "noch kein Gebäudeplan")
        v.addWidget(label(
            f"<b>Neuer Gebäudeplan</b> = die Datei, die Sie jetzt übernehmen wollen: {herkunft(neu)} – "
            f"{len(neu.zimmer)} Zimmer, {belegt} Belegungen (Export aus dem Belegungssystem).<br>"
            f"<b>Jetzt im Zimmerplan</b> = was dieses Programm gerade zeigt: {bisher} plus die "
            f"<b>eigenen Einträge</b> (im Programm geplant: Zuteilen, Assistenz, Mieter, Umzüge).<br>"
            "Verglichen wird ab heute. Am Belegungssystem selbst ändert sich nichts.", "muted", umbruch=True))
        entscheiden = [u for u in self.unterschiede if u.entscheidbar]
        v.addWidget(Hinweis(pa.zusammenfassung(self.unterschiede)
                            + (f" – bei {len(entscheiden)} bitte wählen, was gelten soll." if entscheiden else ""),
                            "warnung" if entscheiden else "info"))
        if entscheiden:
            alle = QHBoxLayout()
            alle.addWidget(label("Für alle:", "fett"))
            plan = knopf("Alles aus dem neuen Gebäudeplan übernehmen", "ghost", None,
                         "Zimmer und Zeiträume laut neuem Gebäudeplan; eigene Einträge, die dort fehlen oder doppelt "
                         "belegen, werden gelöscht")
            plan.clicked.connect(lambda: self._alle("plan"))
            planung = knopf("Alle eigenen Einträge behalten", "ghost", None,
                            "Für diese Personen gilt weiter, was im Programm eingetragen ist")
            planung.clicked.connect(lambda: self._alle("planung"))
            alle.addWidget(plan)
            alle.addWidget(planung)
            alle.addStretch()
            v.addLayout(alle)
        self.tab = Tabelle(["Art", "Person", "Zimmerplan jetzt", "Neuer Gebäudeplan", "Was soll gelten?"],
                           ["l", "l", "l", "l", "l"], dehnen=2)
        self._wahl: list[tuple[pa.Unterschied, QComboBox]] = []
        zeilen = []
        for u in self.unterschiede:
            if u.entscheidbar:
                box = QComboBox()
                for schluessel, text in u.optionen.items():
                    box.addItem(text, schluessel)
                box.setCurrentIndex(list(u.optionen).index(u.wahl))
                box.currentIndexChanged.connect(lambda _i, u=u, box=box: (setattr(u, "wahl", box.currentData()),
                                                                           box.setToolTip(box.currentText())))
                box.setToolTip(box.currentText())
                self._wahl.append((u, box))
                wahl = box
            else:
                wahl = ("wird aus dem neuen Gebäudeplan übernommen" if u.art != "neu"
                        else "kommt aus dem neuen Gebäudeplan dazu")
            zeilen.append([u.art_text, u.name, u.system or "–", u.plan or "–", wahl])
        self.tab.fuellen(zeilen)
        self.tab.widgets_einpassen()
        self.tab.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)   # beide Vergleichsspalten wachsen
        kh = self.tab.horizontalHeader()
        for c, breite in ((0, 130), (1, 140), (4, 390)):   # feste Breite, Text bricht um; Rest für den Vergleich
            kh.setSectionResizeMode(c, QHeaderView.Fixed)
            self.tab.setColumnWidth(c, breite)
        self.tab.setWordWrap(True)                     # lange Zimmer-/Zeitangaben umbrechen statt „…“
        self.tab.resizeRowsToContents()
        for r, u in enumerate(self.unterschiede):
            for c in range(4):
                if self.tab.item(r, c):
                    self.tab.item(r, c).setToolTip(u.text)
        self.tab.setVisible(bool(self.unterschiede))
        v.addWidget(self.tab, 1)
        if not self.unterschiede:
            v.addStretch()
        v.addWidget(label("Wählen Sie „… lassen/behalten“, gilt im Zimmerplan weiter der eigene Eintrag, auch wenn der "
                          "neue Gebäudeplan etwas anderes sagt. Alles andere kommt aus dem neuen Gebäudeplan. Nach dem "
                          "Übernehmen nimmt Strg+Z alles zurück.", "klein", umbruch=True))
        knoepfe = QHBoxLayout()
        knoepfe.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.setToolTip("Nichts übernehmen – der bisherige Gebäudeplan bleibt")
        abbrechen.clicked.connect(self.reject)
        ok = knopf("Übernehmen", "primary", "haken")
        ok.clicked.connect(self.accept)
        knoepfe.addWidget(abbrechen)
        knoepfe.addWidget(ok)
        v.addLayout(knoepfe)

    def _alle(self, vorrang: str) -> None:
        for u, box in self._wahl:
            ziel = vorrang if vorrang in u.optionen else ("entfernen" if vorrang == "plan" else "planung")
            if ziel in u.optionen:
                box.setCurrentIndex(list(u.optionen).index(ziel))


def plan_pruefen(parent, zustand, neu) -> list[pa.Unterschied] | None:
    """Maske zeigen. Die Unterschiede samt Wahl, wenn „Übernehmen“ – sonst None (nichts geändert)."""
    dlg = PlanAbgleichDialog(zustand, neu, zp.laden(), parent)
    if dlg.exec() != QDialog.Accepted:
        zustand.meldung.emit("Gebäudeplan nicht übernommen – es bleibt der bisherige.", "info")
        return None
    return dlg.unterschiede


def plan_uebernehmen(zustand, neu, unterschiede: list[pa.Unterschied], quelle: dict | None = None) -> None:
    """Mit den gewählten Vorrängen übernehmen – als ein Schritt, den Strg+Z zurücknimmt (samt Gebäudeplan)."""
    vorher = aenderungen.schnappschuss(aenderungen.dateien_mit_plan())
    n = pa.anwenden(neu, unterschiede, quelle)
    aenderungen.merken("Gebäudeplan übernommen", vorher)
    belegt = sum(1 for b in neu.belegungen if b.art == "belegt")
    zustand.aenderung_gespeichert.emit(
        f"Gebäudeplan übernommen: {len(neu.zimmer)} Zimmer, {belegt} Belegungen"
        + (f", {n} Entscheidung(en) zu eigenen Einträgen umgesetzt." if n else "."), "ok")
    zustand.zimmer_geaendert.emit()
