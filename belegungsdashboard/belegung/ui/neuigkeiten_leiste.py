"""Glocke oben rechts + Leiste „Neuigkeiten“ am rechten Rand (ein-/ausblendbar).

Die Glocke zeigt, wie viele Neuigkeiten ungelesen sind, und blendet die Leiste ein oder aus. Ein Klick auf eine
Neuigkeit führt dorthin, wo sie bearbeitet wird, und markiert sie als gelesen; ✕ entfernt sie.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from .. import neuigkeiten as nk
from . import theme
from .widgets import knopf, label, leeren

BREITE = 310


def _wann(t: datetime, jetzt: datetime | None = None) -> str:
    jetzt = jetzt or datetime.now()
    s = (jetzt - t).total_seconds()
    if s < 90:
        return "gerade eben"
    if s < 3600:
        return f"vor {int(s // 60)} Min."
    if t.date() == jetzt.date():
        return f"heute {t:%H:%M}"
    if (jetzt.date() - t.date()).days == 1:
        return f"gestern {t:%H:%M}"
    return f"{t:%d.%m. %H:%M}"


class NeuigkeitenLeiste(QFrame):
    oeffnen = Signal(str)           # Ziel, z. B. „termine“ oder „zimmerplan:Reinigung“
    geaendert = Signal()            # Zähler der Glocke neu

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("neuigkeiten")
        self.setFixedWidth(BREITE)
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 16, 12, 12)
        v.setSpacing(8)
        kopf = QHBoxLayout()
        kopf.addWidget(label("Neuigkeiten", "kartentitel"))
        kopf.addStretch()
        self.b_gelesen = knopf("", "icon", "haken", "Alle als gelesen markieren")
        self.b_gelesen.clicked.connect(lambda: (nk.gelesen_setzen(), self.aktualisieren()))
        kopf.addWidget(self.b_gelesen)
        self.b_leeren = knopf("", "icon", "loeschen", "Alle entfernen")
        self.b_leeren.clicked.connect(lambda: (nk.entfernen(), self.aktualisieren()))
        kopf.addWidget(self.b_leeren)
        zu = knopf("", "icon", "schliessen", "Leiste ausblenden (Glocke oben rechts blendet sie wieder ein)")
        zu.clicked.connect(self.hide)
        kopf.addWidget(zu)
        v.addLayout(kopf)
        v.addWidget(label("Was im Hintergrund passiert ist – Klick führt hin.", "klein", umbruch=True))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inhalt = QWidget()
        inhalt.setObjectName("neuigkeiten_inhalt")
        self.liste = QVBoxLayout(inhalt)
        self.liste.setContentsMargins(0, 4, 0, 4)
        self.liste.setSpacing(2)
        scroll.setWidget(inhalt)
        v.addWidget(scroll, 1)
        self.theme_setzen()

    def theme_setzen(self) -> None:
        t = theme.T
        self.setStyleSheet(f"QFrame#neuigkeiten {{ background: {t.surface}; border-left: 1px solid {t.border}; }}"
                           "QWidget#neuigkeiten_inhalt { background: transparent; }")

    def aktualisieren(self) -> None:
        leeren(self.liste)
        alle = nk.laden()
        t = theme.T
        if not alle:
            self.liste.addWidget(label("Nichts Neues.", "muted"))
        for n in alle[:60]:
            self.liste.addWidget(self._zeile(n, t))
        self.liste.addStretch()
        self.b_gelesen.setEnabled(any(not n.gelesen for n in alle))
        self.b_leeren.setEnabled(bool(alle))
        self.geaendert.emit()

    def _zeile(self, n: nk.Neuigkeit, t) -> QWidget:
        w = QFrame()
        w.setObjectName("nzeile")
        w.setCursor(Qt.PointingHandCursor if n.ziel else Qt.ArrowCursor)
        w.setStyleSheet(f"QFrame#nzeile {{ border-radius: 8px; }} QFrame#nzeile:hover {{ background: "
                        f"{theme.alpha(t.accent, .08)}; }}")
        h = QHBoxLayout(w)
        h.setContentsMargins(6, 6, 2, 6)
        h.setSpacing(8)
        farbe = {"fehler": t.ueber, "warnung": t.knapp, "ok": t.ok}.get(n.art, t.accent)
        punkt = QLabel("●")
        punkt.setStyleSheet(f"color: {farbe if not n.gelesen else theme.alpha(t.text_3, .45)}; font-size: 9px;")
        h.addWidget(punkt, 0, Qt.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(1)
        haupt = label(n.text, "fett" if not n.gelesen else None, umbruch=True)
        text.addWidget(haupt)
        text.addWidget(label(_wann(n.zeit), "klein"))
        h.addLayout(text, 1)
        weg = knopf("", "icon", "schliessen", "Entfernen")
        weg.setFixedSize(24, 24)
        weg.clicked.connect(lambda _=False, i=n.id: (nk.entfernen(i), self.aktualisieren()))
        h.addWidget(weg, 0, Qt.AlignTop)
        for lbl in w.findChildren(QLabel):    # Klick auf den Text zählt als Klick auf die Zeile
            lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        w.mousePressEvent = lambda _e, n=n: self._klick(n)
        return w

    def _klick(self, n: nk.Neuigkeit) -> None:
        nk.gelesen_setzen(n.id)
        self.aktualisieren()
        if n.ziel:
            self.oeffnen.emit(n.ziel)
