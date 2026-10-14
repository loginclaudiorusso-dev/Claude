"""Dialog „Belegung optimieren“: Vorschläge mit Begründung prüfen, auswählen und übernehmen."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QMessageBox, QSizePolicy, QVBoxLayout, QWidget

from .. import eintragen
from .. import optimierung as opt
from .. import zimmerplan as zp
from .widgets import FlowLayout, Karte, Pille, Segment, knopf, label, leeren

ZEITRAEUME = [("8 Wochen", 56), ("6 Monate", 182), ("12 Monate", 365)]
ART_STUFE = {"regel": "ueber", "umzug": "ok", "tausch": "akzent", "zusammen": "akzent", "umbuchen": "knapp"}
ART_TEXT = {
    "regel": "Zimmer verletzt eine feste Regel – mit freiem, passendem Ersatz",
    "umzug": "Geplant und noch nicht angereist: ein anderes Zimmer passt deutlich besser",
    "tausch": "Zwei geplante Personen tauschen – beide Zimmer passen über Kreuz besser",
    "zusammen": "Zwei Bewohner aus verschiedenen Kursen tauschen die Zimmer – danach wohnen beide näher bei ihrem Kurs. "
                "Wird als zwei verbundene Umzüge am Umzugstag angelegt (unter Aufgaben → Eintragen, bis abgeschlossen).",
    "umbuchen": "Im Belegungssystem gebucht: deutlich besseres Zimmer frei – wird als Aufgabe angelegt",
}


class OptimierenDialog(QDialog):
    def __init__(self, zustand, parent=None):
        super().__init__(parent)
        self.z = zustand
        self.setWindowTitle("Belegung optimieren")
        self._auswahl: list[tuple[QCheckBox, opt.Vorschlag]] = []
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Belegung optimieren", "seitentitel"))
        v.addWidget(label("Prüft alle Belegungen im gewählten Zeitraum wie beim Zuteilen – Haus und Etage passend zur "
                          "Gruppe, Reserven (Tier-, Doppel-, EMR-Zimmer), nahtlose Folgebelegung, lange Aufenthalte "
                          "auf einen Flur und jeder Kurs zusammen auf einem Flur (ohne Personen mit Tier). Geplante Zimmer werden nach Bestätigung umgeplant; Buchungen im "
                          "Belegungssystem bekommen eine Aufgabe.", "muted", umbruch=True))
        zeile = QHBoxLayout()
        zeile.addWidget(label("Zeitraum", "fett"))
        self.zeitraum = Segment([t for t, _d in ZEITRAEUME], 1)
        self.zeitraum.geaendert.connect(lambda _i: self.berechnen())
        zeile.addWidget(self.zeitraum)
        zeile.addSpacing(16)
        self.tag_label = label("Umzugstag für Tausche", "fett")
        zeile.addWidget(self.tag_label)
        from datetime import timedelta

        from .widgets import DatumFeld

        self.umzugstag = DatumFeld(date.today() + timedelta(days=7))
        self.umzugstag.setToolTip("An diesem Tag ziehen beide Bewohner eines Tausches um")
        zeile.addWidget(self.umzugstag)
        zeile.addStretch()
        neu = knopf("Neu berechnen", "ghost", "aktualisieren")
        neu.clicked.connect(self.berechnen)
        zeile.addWidget(neu)
        v.addLayout(zeile)
        self.pillen = QWidget()
        self.pillen.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)      # nicht in die Höhe wachsen
        self._pillen = FlowLayout(self.pillen, abstand=6)
        v.addWidget(self.pillen)
        self.liste = QVBoxLayout()
        self.liste.setSpacing(12)
        v.addLayout(self.liste)
        v.addStretch()
        unten = QHBoxLayout()
        alle = knopf("Alle umplanbaren wählen", "ghost")
        alle.clicked.connect(lambda: [cb.setChecked(True) for cb, x in self._auswahl if x.umsetzbar])
        keine = knopf("Keine", "ghost")
        keine.clicked.connect(lambda: [cb.setChecked(False) for cb, _x in self._auswahl])
        unten.addWidget(alle)
        unten.addWidget(keine)
        unten.addStretch()
        zu = knopf("Schließen", "ghost")
        zu.clicked.connect(self.reject)
        self.b_ok = knopf("Ausgewählte übernehmen", "primary", "haken")
        self.b_ok.clicked.connect(self._uebernehmen)
        unten.addWidget(zu)
        unten.addWidget(self.b_ok)
        v.addLayout(unten)
        from .dialoge import scrollbar_machen

        scrollbar_machen(self, 900, 760)
        self.berechnen()

    def berechnen(self) -> None:
        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.stand = zp.laden()
            self.vorschlaege = opt.vorschlaege(self.stand, date.today(), ZEITRAEUME[self.zeitraum.index()][1],
                                               haken=eintragen._haken())
        finally:
            QGuiApplication.restoreOverrideCursor()
        self._zeigen()

    def _zeigen(self) -> None:
        leeren(self._pillen)
        leeren(self.liste)
        self._auswahl = []
        for art, name in opt.ARTEN.items():
            n = sum(1 for x in self.vorschlaege if x.art == art)
            if n:
                self._pillen.addWidget(Pille(f"{n} × {name}", ART_STUFE[art]))
        if not self.vorschlaege:
            self.liste.addWidget(label("Keine Vorschläge – die Belegung passt so, wie sie ist.", "muted"))
        for art, name in opt.ARTEN.items():
            gruppe = [x for x in self.vorschlaege if x.art == art]
            if not gruppe:
                continue
            karte = Karte(name, ART_TEXT[art])
            for x in gruppe:
                karte.inhalt.addWidget(self._zeile(x))
            self.liste.addWidget(karte)
        hat = any(x.art == "zusammen" for x in self.vorschlaege)
        self.tag_label.setVisible(hat)
        self.umzugstag.setVisible(hat)
        self._zaehlen()

    def _zeile(self, x: opt.Vorschlag) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(10)
        cb = QCheckBox()
        cb.setChecked(x.vorauswahl)
        cb.setToolTip("Umplanen" if x.umsetzbar else "Aufgabe „im Belegungssystem umbuchen“ anlegen")
        cb.toggled.connect(lambda _a: self._zaehlen())
        self._auswahl.append((cb, x))
        h.addWidget(cb, 0, Qt.AlignTop)
        texte = QVBoxLayout()
        texte.setSpacing(2)
        texte.addWidget(label(f"<b>{x.text}</b>", umbruch=True))
        texte.addWidget(label(f"{x.zeitraum} · Verbesserung +{x.gewinn:g} Punkte"
                              + ("" if x.umsetzbar else " · wird als Aufgabe angelegt"), "klein", umbruch=True))
        if x.gruende:
            texte.addWidget(label(" · ".join(x.gruende), "muted", umbruch=True))
        if x.hinweis:
            hin = label(f"⚠ {x.hinweis}", "klein", umbruch=True)
            texte.addWidget(hin)
        h.addLayout(texte, 1)
        ansehen = knopf("Zimmer ansehen", "ghost", "haus", f"Zimmerkarte {x.nach_zimmer[0].removeprefix('GS-')}")
        ansehen.clicked.connect(lambda: self._karte(x.nach_zimmer[0]))
        h.addWidget(ansehen, 0, Qt.AlignTop)
        return w

    def _karte(self, zid: str) -> None:
        from .zimmerkarte import karte_oeffnen

        karte_oeffnen(self.parent(), self.z, zid)

    def _zaehlen(self) -> None:
        n = sum(1 for cb, _x in self._auswahl if cb.isChecked())
        self.b_ok.setText(f"Ausgewählte übernehmen ({n})" if n else "Ausgewählte übernehmen")
        self.b_ok.setEnabled(bool(n))

    def _uebernehmen(self) -> None:
        gewaehlt = [x for cb, x in self._auswahl if cb.isChecked()]
        if not gewaehlt:
            return
        tausch = [x for x in gewaehlt if x.art == "zusammen"]
        um = [x for x in gewaehlt if x.umsetzbar and x.art != "zusammen"]
        auf = [x for x in gewaehlt if not x.umsetzbar]
        text = ((f"{len(um)} Planung(en) ändern:\n• " + "\n• ".join(x.text for x in um[:12]) + "\n\n") if um else "") + \
               ((f"{len(tausch)} Tausch(e) = {2 * len(tausch)} Umzüge am {self.umzugstag.datum():%d.%m.%Y}:\n• "
                 + "\n• ".join(x.text for x in tausch[:8]) + (" …" if len(tausch) > 8 else "") + "\n\n") if tausch else "") + \
               (f"{len(auf)} Aufgabe(n) „im Belegungssystem umbuchen“ anlegen." if auf else "")
        if QMessageBox.question(self, "Übernehmen", text.strip()) != QMessageBox.Yes:
            return
        n, a, t = opt.umsetzen(self.stand, gewaehlt, umzugstag=self.umzugstag.datum())
        teile = ([f"{n} Planung(en) geändert"] if n else []) + \
                ([f"{t} Tausch(e) = {2 * t} Umzüge am {self.umzugstag.datum():%d.%m.%Y}"] if t else []) + \
                ([f"{a} Aufgabe(n) angelegt"] if a else [])
        self.z.meldung.emit("Optimierung: " + ("; ".join(teile) or "nichts geändert") + ".", "ok")
        self.z.zimmer_geaendert.emit()
        self.z.termine_geaendert.emit()
        self.berechnen()
