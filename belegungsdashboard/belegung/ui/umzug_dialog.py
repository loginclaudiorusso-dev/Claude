"""Dialog „Umzug planen“: Wer schon eingezogen ist, wechselt ab einem Tag in ein anderes Zimmer.

Geöffnet aus dem Zeitstrahl (Balken in ein anderes Zimmer ziehen oder Rechtsklick → Umzug) und aus der
Zimmer-/Personenkarte. Die Logik steht in ``belegung/umzug.py``.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QVBoxLayout

from .. import umzug as um
from .. import zimmerplan as zp
from .widgets import DatumFeld, Hinweis, knopf, label, leeren


class UmzugDialog(QDialog):
    def __init__(self, zustand, zid: str = "", schluessel: str = "", name: str = "", nach: str | None = None,
                 ab: date | None = None, uid: str | None = None, parent=None):
        super().__init__(parent)
        self.z, self.uid = zustand, uid
        self.stand = zp.laden(ohne_umzug=uid)
        alt = next((u for u in um.laden() if u.id == uid), None) if uid else None
        if alt is not None:
            self.bel = um.quelle_finden(self.stand.lage, alt)
            nach = nach or alt.nach_zimmer
            ab = ab or alt.ab
        else:
            self.bel = um.belegung_zu(self.stand, zid, schluessel, name)
        self.setWindowTitle("Umzug ändern" if alt else "Umzug planen")
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Umzug ändern" if alt else "Umzug planen", "seitentitel"))
        if self.bel is None:
            v.addWidget(Hinweis("Die Belegung wurde nicht mehr gefunden – vielleicht ist die Person schon abgereist "
                                "oder der Gebäudeplan hat sich geändert.", "fehler"))
            unten = QHBoxLayout()
            unten.addStretch()
            if alt is not None:
                weg = knopf("Umzug löschen", "ghost")
                weg.clicked.connect(self._zuruecknehmen)
                unten.addWidget(weg)
            zu = knopf("Schließen", "ghost")
            zu.clicked.connect(self.reject)
            unten.addWidget(zu)
            v.addLayout(unten)
            return
        b = self.bel
        quelle = "Gebäudeplan (Belegungssystem)" if b.art == "belegt" else "Zimmerplan (geplant)"
        v.addWidget(label(f"<b>{b.name}</b>" + (f" · {b.massnahme}" if b.massnahme else ""), umbruch=True))
        v.addWidget(label(f"Wohnt in {b.zimmer.removeprefix('GS-')} vom {b.von:%d.%m.%Y} bis {b.bis:%d.%m.%Y} · {quelle}",
                          "muted", umbruch=True))
        raster = QGridLayout()
        raster.setHorizontalSpacing(12)
        raster.setVerticalSpacing(10)
        raster.addWidget(label("Umzug am", "fett"), 0, 0)
        self.tag = DatumFeld(min(max(ab or um.standard_tag(b), b.von), b.bis))
        self.tag.geaendert.connect(lambda _d: self._zimmer_fuellen())
        zeile = QHBoxLayout()
        zeile.addWidget(self.tag)
        zeile.addWidget(label("Auszug alt und Einzug neu am selben Tag", "klein"))
        zeile.addStretch()
        raster.addLayout(zeile, 0, 1)
        raster.addWidget(label("Neues Zimmer", "fett"), 1, 0)
        self.zimmer = QComboBox()
        self.zimmer.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.zimmer.setMinimumContentsLength(26)
        self.zimmer.currentIndexChanged.connect(lambda _i: self._pruefen())
        raster.addWidget(self.zimmer, 1, 1)
        raster.addWidget(label("Grund", "fett"), 2, 0)
        self.grund = QLineEdit(alt.grund if alt else "")
        self.grund.setPlaceholderText("optional, z. B. „Heizung defekt“, „Wunsch: ruhiger“")
        raster.addWidget(self.grund, 2, 1)
        raster.setColumnStretch(1, 1)
        v.addLayout(raster)
        self.belegt = QCheckBox("Umzug steht fest bzw. ist erfolgt – Planung abschließen (fest)")
        self.belegt.setToolTip("Fest: gilt sofort als belegt, auch ohne neuen Gebäudeplan, und fällt aus Aufgaben → Eintragen "
                               "heraus. Geplant: steht als Aufgabe zum Umbuchen im Belegungssystem.")
        self.belegt.setChecked(alt.belegt if alt else (ab is not None and ab <= date.today()))
        v.addWidget(self.belegt)
        self.status = QVBoxLayout()
        v.addLayout(self.status)
        v.addWidget(label("Fest gilt der Umzug sofort – ein neuer Gebäudeplan ist dafür nicht nötig. Als geplant "
                          "steht er unter Aufgaben → Eintragen, bis er im Belegungssystem umgebucht ist. Zeigt ein "
                          "späterer Gebäudeplan die Person im neuen Zimmer, ist er erledigt.", "klein", umbruch=True))
        unten = QHBoxLayout()
        if alt is not None:
            weg = knopf("Umzug zurücknehmen", "ghost")
            weg.setToolTip("Die Person bleibt im alten Zimmer")
            weg.clicked.connect(self._zuruecknehmen)
            unten.addWidget(weg)
        unten.addStretch()
        ab_k = knopf("Abbrechen", "ghost")
        ab_k.clicked.connect(self.reject)
        self.ok = knopf("Umzug speichern", "primary", "haken")
        self.ok.clicked.connect(self._speichern)
        unten.addWidget(ab_k)
        unten.addWidget(self.ok)
        v.addLayout(unten)
        self._nach = nach
        self._zimmer_fuellen()
        self.resize(620, self.sizeHint().height())

    def _zimmer_fuellen(self) -> None:
        gewaehlt = self.zimmer.currentData() or self._nach
        self.zimmer.blockSignals(True)
        self.zimmer.clear()
        gut, ausnahmen = um.auswahl(self.stand, self.bel, self.tag.datum())
        ids = {z.id for z in gut} | {z.id for z, _g in ausnahmen}
        if gewaehlt and gewaehlt not in ids and gewaehlt in self.stand.lage.zimmer:
            self.zimmer.addItem(f"{self.stand.lage.zimmer[gewaehlt].kurz} · geht nicht", gewaehlt)
        for z in gut:
            self.zimmer.addItem(f"{z.kurz} · {zp.flur_text(z)}", z.id)
        if ausnahmen:
            self.zimmer.insertSeparator(self.zimmer.count())
            for z, grund in ausnahmen:
                self.zimmer.addItem(f"{z.kurz} · Ausnahme: {grund}", z.id)
                self.zimmer.setItemData(self.zimmer.count() - 1, f"Ausnahme: {grund}", Qt.ToolTipRole)
        if self.zimmer.count() == 0:
            self.zimmer.addItem("– kein Zimmer frei –", "")
        self.zimmer.setCurrentIndex(max(0, self.zimmer.findData(gewaehlt)) if gewaehlt else 0)
        self.zimmer.blockSignals(False)
        self._pruefen()

    def _pruefen(self) -> None:
        leeren(self.status)
        nach = self.zimmer.currentData() or ""
        if not nach:
            self.status.addWidget(Hinweis("Ab diesem Tag ist kein anderes Zimmer bis zur Abreise frei.", "fehler"))
            self.ok.setEnabled(False)
            return
        self._nach = nach
        fehler, hinweis = um.pruefen(self.stand, self.bel, nach, self.tag.datum())
        if fehler:
            self.status.addWidget(Hinweis(fehler, "fehler"))
        elif hinweis:
            self.status.addWidget(Hinweis(f"Geht nur als Ausnahme: {hinweis}", "warnung"))
        else:
            b, z = self.bel, self.stand.lage.zimmer[nach]
            self.status.addWidget(Hinweis(f"{b.zimmer.removeprefix('GS-')} bis {self.tag.datum():%d.%m.} (dann "
                                          f"Auszugsreinigung), {z.kurz} ab {self.tag.datum():%d.%m.} bis "
                                          f"{b.bis:%d.%m.%Y}.", "info"))
        self.ok.setEnabled(fehler is None)

    def _speichern(self) -> None:
        nach, tag = self.zimmer.currentData() or "", self.tag.datum()
        fehler, hinweis = um.pruefen(self.stand, self.bel, nach, tag)
        if fehler:
            return
        if hinweis and QMessageBox.question(self, "Ausnahme", f"{hinweis}\n\nTrotzdem dorthin umziehen?") != QMessageBox.Yes:
            return
        from .aenderung_ui import ausfuehren

        self.ok.setEnabled(False)                 # kein Doppelklick → kein doppelter Umzug
        b, z = self.bel, self.stand.lage.zimmer[nach]
        titel = f"Umzug {b.name}: {b.zimmer.removeprefix('GS-')} → {z.kurz} ab {tag:%d.%m.}"
        if ausfuehren(self, self.z, titel,
                      lambda: um.speichern(self.stand, self.bel, nach, tag, self.grund.text(), self.uid,
                                           belegt=self.belegt.isChecked()),
                      lambda u: f"Umzug fest: {u.text}." if u.belegt else
                      f"Umzug geplant: {u.text}. Im Belegungssystem umbuchen (Aufgaben → Eintragen).",
                      "warnung" if hinweis else "ok"):
            self.z.zimmer_geaendert.emit()
            self.accept()
        else:
            self.ok.setEnabled(True)

    def _zuruecknehmen(self) -> None:
        if zurueck_nehmen(self, self.z, self.uid):
            self.accept()


def umzug_oeffnen(parent, zustand, **kw) -> bool:
    return UmzugDialog(zustand, parent=parent, **kw).exec() == QDialog.Accepted


def zurueck_nehmen(parent, zustand, uid: str) -> bool:
    from .aenderung_ui import ausfuehren

    u = next((x for x in um.laden() if x.id == uid), None)
    if u is None:
        zustand.meldung.emit("Dieser Umzug ist schon entfernt.", "info")
        return False
    tausch = next((x for x in um.laden() if u.partner and x.id == u.partner), None)
    text = (f"Umzug zurücknehmen?\n\n{u.text}\n→ {u.name} bleibt in {u.von_zimmer.removeprefix('GS-')}, "
            f"{u.nach_zimmer.removeprefix('GS-')} ist wieder frei.")
    if tausch is not None:
        text += f"\n\nTeil eines Tauschs – der Gegen-Umzug wird mit zurückgenommen:\n{tausch.text}"
    if QMessageBox.question(parent, "Umzug zurücknehmen", text) != QMessageBox.Yes:
        return False
    ok = ausfuehren(parent, zustand, f"Umzug {u.name} zurückgenommen", lambda: um.entfernen(uid),
                    f"Umzug zurückgenommen: {u.name} bleibt in {u.von_zimmer.removeprefix('GS-')}"
                    + (f" (Tausch mit {tausch.name} ebenso)." if tausch else "."))
    if ok:
        zustand.zimmer_geaendert.emit()
    return ok
