"""Dialog „Abgleich mit der Zimmerkontrollliste (ZKL)“: Abweichungen ansehen, übernehmen oder als geprüft ablegen."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QMessageBox, QSizePolicy, QVBoxLayout, QWidget

from .. import zimmerplan as zp
from .. import zkl
from .widgets import FlowLayout, Karte, Pille, knopf, label

STUFE = {"bewohnt": "ueber", "nicht_belegbar": "knapp", "gaeste": "neutral", "tiere": "akzent",
         "anderes_zimmer": "ok", "unbekannt": "neutral"}
ERKLAERUNG = {
    "bewohnt": "Wichtig vor dem Planen: Steht die Person noch im Belegungssystem? Wenn ja, übernehmen – dann bleibt das "
               "Zimmer bis zur Abreise belegt. Zeigt ein späterer Gebäudeplan die Person, gilt wieder er.",
    "nicht_belegbar": "Übernehmen setzt das Zimmer auf „gehört nicht zum Internat“ (Stammdaten, jederzeit änderbar).",
    "gaeste": "Im Zimmerplan sind nur die Zimmer in Haus 2, 6. OG Gästezimmer. Nur übernehmen, wenn das Zimmer "
              "wirklich zum Gästehaus gehört.",
    "tiere": "Tier-Zimmer werden für Personen mit Tier freigehalten. Laut ZKL gehören nur diese Zimmer zum Tier-Pool.",
    "anderes_zimmer": "Nur zur Info – der Gebäudeplan ist neuer und gilt.",
    "unbekannt": "Lager, RST, Jugendhilfe u. Ä. – stehen nicht im Gebäudeplan und werden nicht geplant.",
}


class ZklAbgleichDialog(QDialog):
    def __init__(self, zustand, parent=None, alle: bool = False):
        super().__init__(parent)
        self.z = zustand
        self.setWindowTitle("Abgleich mit der ZKL")
        self.stand = zp.laden()
        self.daten = zkl.laden()
        self.punkte = zkl.abgleich(self.stand, self.daten, alle=alle) if self.daten else []
        self._wahl: list[tuple[QCheckBox, zkl.Punkt]] = []
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Abgleich mit der Zimmerkontrollliste", "seitentitel"))
        if self.daten:
            stand = f", Daten bis {self.daten.stand:%d.%m.%Y}" if self.daten.stand else ""
            v.addWidget(label(f"<b>{self.daten.datei}</b> · Blatt „{self.daten.blatt}“{stand}. Der Gebäudeplan bleibt "
                              "die Grundlage; aus der ZKL kommen Tier, TN-Nummer und Zimmer-Infos automatisch dazu. "
                              "Hier entscheidest du die Abweichungen – angehakt wird übernommen, der Rest als geprüft "
                              "abgelegt.", "muted", umbruch=True))
        pillen = QWidget()
        pillen.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)   # umbrechen statt verbreitern
        fl = FlowLayout(pillen, abstand=6)
        for art, name in zkl.ARTEN.items():
            n = sum(1 for p in self.punkte if p.art == art)
            if n:
                fl.addWidget(Pille(f"{n} × {name}", STUFE[art]))
        v.addWidget(pillen)
        if not self.punkte:
            v.addWidget(label("Keine offenen Abweichungen – ZKL und Zimmerplan passen zusammen.", "muted"))
        for art, name in zkl.ARTEN.items():
            gruppe = [p for p in self.punkte if p.art == art]
            if not gruppe:
                continue
            karte = Karte(name, ERKLAERUNG[art])
            for p in gruppe:
                if p.aktion:                   # Kästchen + umbrechender Text (QCheckBox bricht nicht um)
                    zeile = QHBoxLayout()
                    zeile.setSpacing(8)
                    cb = QCheckBox()
                    text = label(f"{p.text} → <b>{p.aktion}</b>", umbruch=True)
                    text.mousePressEvent = lambda _e, c=cb: c.toggle()
                    self._wahl.append((cb, p))
                    zeile.addWidget(cb, 0, Qt.AlignTop)
                    zeile.addWidget(text, 1)
                    karte.inhalt.addLayout(zeile)
                else:
                    karte.inhalt.addWidget(label(p.text, umbruch=True))
            if sum(1 for p in gruppe if p.aktion) > 3:
                alle_k = knopf("Alle in dieser Gruppe wählen", "ghost")
                alle_k.clicked.connect(lambda _c=False, a=art: [cb.setChecked(True) for cb, p in self._wahl if p.art == a])
                karte.inhalt.addWidget(alle_k, 0, Qt.AlignLeft)
            v.addWidget(karte)
        v.addStretch()
        unten = QHBoxLayout()
        if not alle:
            alt = knopf("Auch geprüfte zeigen", "ghost")
            alt.clicked.connect(self._alle)
            unten.addWidget(alt)
        unten.addStretch()
        zu = knopf("Schließen", "ghost")
        zu.clicked.connect(self.reject)
        self.ok = knopf("Übernehmen", "primary", "haken")
        self.ok.setToolTip("Angehakte übernehmen, alle übrigen als geprüft ablegen")
        self.ok.clicked.connect(self._uebernehmen)
        self.ok.setEnabled(bool(self.punkte))
        unten.addWidget(zu)
        unten.addWidget(self.ok)
        v.addLayout(unten)
        from .dialoge import scrollbar_machen

        scrollbar_machen(self, 860, 760)

    def _alle(self) -> None:
        self.reject()
        ZklAbgleichDialog(self.z, self.parent(), alle=True).exec()

    def _uebernehmen(self) -> None:
        gewaehlt = [p for cb, p in self._wahl if cb.isChecked()]
        rest = [p for p in self.punkte if p not in gewaehlt]
        if QMessageBox.question(self, "Übernehmen", f"{len(gewaehlt)} Abweichung(en) übernehmen, {len(rest)} als geprüft "
                                "ablegen?") != QMessageBox.Yes:
            return
        n = zkl.umsetzen(self.stand, self.daten, gewaehlt, rest)
        teile = [f"{k} × {zkl.ARTEN[a].split(' (')[0]}" for a, k in n.items()]
        self.z.meldung.emit("ZKL-Abgleich: " + ("; ".join(teile) if teile else "alles als geprüft abgelegt") + ".", "ok")
        self.z.zimmer_geaendert.emit()
        self.accept()
