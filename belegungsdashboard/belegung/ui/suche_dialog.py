"""Suchfenster für Namen: Treffer aus allen Quellen, mit Zimmer, Zeitraum und Sprung ins Zimmer bzw. zur Person."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QVBoxLayout

from .. import suche, termine
from .. import zimmerplan as zp
from .widgets import Tabelle, knopf, label


class SuchDialog(QDialog):
    def __init__(self, fenster, text: str = ""):
        super().__init__(fenster)
        self.fenster = fenster
        self.setWindowTitle("Suchen – Name oder Zimmer")
        self.resize(1000, 560)
        self.stand = zp.laden()
        self.treffer: list[suche.Treffer] = []
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(12)
        self.feld = QLineEdit(text)
        self.feld.setPlaceholderText("Name („Meier“, „Anna Kolmer“) oder Zimmer („322“, „2-322“, „E01“)")
        self.feld.setClearButtonEnabled(True)
        self._timer = QTimer(self, singleShot=True, interval=200)
        self._timer.timeout.connect(self._suchen)
        self.feld.textChanged.connect(lambda _t: self._timer.start())
        v.addWidget(self.feld)
        self.info = label("", "klein")
        v.addWidget(self.info)
        self.tab = Tabelle(["Name", "Maßnahme", "Zimmer", "Zeitraum", "Status", "Quelle", "Notiz"],
                           ["l", "l", "l", "l", "l", "l", "l"], dehnen=6)
        self.tab.setTextElideMode(Qt.ElideRight)
        self.tab.itemSelectionChanged.connect(self._auswahl)
        self.tab.doubleClicked.connect(lambda _i: self._oeffnen())
        v.addWidget(self.tab, 1)
        unten = QHBoxLayout()
        self.b_oeffnen = knopf("Öffnen", "primary", "haus")
        self.b_oeffnen.setToolTip("Zimmer- und Personenkarte: Zimmer ändern, Abreise, Notizen mit Wiedervorlage")
        self.b_oeffnen.clicked.connect(self._oeffnen)
        self.b_zeitstrahl = knopf("Im Zeitstrahl", "ghost")
        self.b_zeitstrahl.setToolTip("Zimmerplan → Zeitstrahl mit diesem Zimmer")
        self.b_zeitstrahl.clicked.connect(self._zeitstrahl)
        unten.addWidget(self.b_oeffnen)
        unten.addWidget(self.b_zeitstrahl)
        unten.addStretch()
        zu = knopf("Schließen", "ghost")
        zu.clicked.connect(self.reject)
        unten.addWidget(zu)
        v.addLayout(unten)
        self._suchen()
        self.feld.setFocus()

    def _suchen(self) -> None:
        heute = date.today()
        self.treffer = suche.suchen(self.feld.text(), self.stand)
        zeilen = []
        notizen: dict[str, list[termine.Notiz]] = {}
        for n in termine.notizen():
            notizen.setdefault(n.person, []).append(n)
        for t in self.treffer:
            ns = notizen.get(t.person, []) if t.person else []
            if ns:
                wv = min((n.wiedervorlage for n in ns if n.wiedervorlage and n.wiedervorlage >= heute), default=None)
                t.notiz = " · ".join(x for x in (t.notiz, f"{len(ns)} Notiz{'en' if len(ns) > 1 else ''}"
                                                 + (f" (WV {wv:%d.%m.})" if wv else ""), ns[0].text) if x)
            zeit = f"{t.von:%d.%m.%Y} – " + (f"{t.bis:%d.%m.%Y}" if t.bis else "offen")
            zeilen.append([t.name, t.massnahme or zp.GRUPPE_LABEL.get(t.gruppe, t.gruppe), t.zimmer_text, zeit,
                           t.status(heute), t.quelle, t.notiz])
        self.tab.fuellen(zeilen)
        for r, t in enumerate(self.treffer):
            if t.notiz and self.tab.item(r, 6):
                self.tab.item(r, 6).setToolTip(t.notiz)
        if len(self.feld.text().strip()) < 2:
            self.info.setText("Mindestens 2 Zeichen eingeben – Name oder Zimmernummer.")
        else:
            art = "Zimmer-Suche" if suche.ist_zimmersuche(self.feld.text()) else "Namenssuche"
            self.info.setText(f"{art}: {len(self.treffer)} Treffer"
                              + (" – Doppelklick öffnet Zimmer und Person" if self.treffer else ""))
        if self.treffer:
            self.tab.selectRow(0)
        self._auswahl()

    def _gewaehlt(self) -> suche.Treffer | None:
        zeilen = self.tab.selectionModel().selectedRows() if self.tab.selectionModel() else []
        return self.treffer[zeilen[0].row()] if zeilen and zeilen[0].row() < len(self.treffer) else None

    def _auswahl(self) -> None:
        t = self._gewaehlt()
        self.b_oeffnen.setEnabled(bool(t and (t.zimmer_id or t.person)))
        self.b_zeitstrahl.setEnabled(bool(t and t.zimmer_id))

    def _oeffnen(self) -> None:
        from .zimmerkarte import karte_oeffnen

        t = self._gewaehlt()
        if not t or not (t.zimmer_id or t.person):
            return
        self.accept()
        karte_oeffnen(self.fenster, self.fenster.z, t.zimmer_id or None, t.person or None)

    def _zeitstrahl(self) -> None:
        t = self._gewaehlt()
        if not t or not t.zimmer_id:
            return
        self.accept()
        self.fenster.zeigen("zimmerplan")
        self.fenster.seiten["zimmerplan"].zimmer_im_zeitstrahl(t.zimmer_id)
