"""Suchfenster für Namen: Treffer aus allen Quellen, mit Zimmer, Zeitraum und Sprung ins Zimmer bzw. zur Person."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QVBoxLayout

from .. import suche
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
        self.tab.doubleClicked.connect(lambda _i: self._zimmer())
        v.addWidget(self.tab, 1)
        unten = QHBoxLayout()
        self.b_zimmer = knopf("Zimmer anzeigen", "primary", "haus")
        self.b_zimmer.clicked.connect(self._zimmer)
        self.b_person = knopf("Person öffnen", "ghost")
        self.b_person.setToolTip("Abreise, Erinnerung, Notiz und Angaben der Person bearbeiten")
        self.b_person.clicked.connect(self._person)
        unten.addWidget(self.b_zimmer)
        unten.addWidget(self.b_person)
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
        for t in self.treffer:
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
                              + (" – Doppelklick zeigt das Zimmer" if self.treffer else ""))
        if self.treffer:
            self.tab.selectRow(0)
        self._auswahl()

    def _gewaehlt(self) -> suche.Treffer | None:
        zeilen = self.tab.selectionModel().selectedRows() if self.tab.selectionModel() else []
        return self.treffer[zeilen[0].row()] if zeilen and zeilen[0].row() < len(self.treffer) else None

    def _auswahl(self) -> None:
        t = self._gewaehlt()
        self.b_zimmer.setEnabled(bool(t and t.zimmer_id))
        self.b_person.setEnabled(bool(t and t.person))

    def _zimmer(self) -> None:
        t = self._gewaehlt()
        if not t or not t.zimmer_id:
            return
        self.accept()
        self.fenster.zeigen("zimmerplan")
        self.fenster.seiten["zimmerplan"]._zimmer_details(t.zimmer_id)

    def _person(self) -> None:
        t = self._gewaehlt()
        if not t or not t.person:
            return
        self.fenster.seiten["termine"]._person_oeffnen(t.person)
        self.stand = zp.laden()
        self._suchen()
