"""Notizen mit Wiedervorlage – für eine Person oder ein Zimmer (Ablage: termine.Notiz)."""

from __future__ import annotations

from datetime import date, timedelta
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from .. import termine
from . import theme
from .widgets import DatumFeld, Pille, knopf, label, leeren


class NotizenWidget(QWidget):
    """Liste der Notizen + Eingabezeile. ``sofort``: jede Änderung gleich speichern (Karten);
    sonst gepuffert bis ``speichern()`` (Dialog mit Speichern/Abbrechen)."""

    geaendert = Signal()

    def __init__(self, schluessel: str, name: str, sofort: bool = True, platzhalter: str = "", parent=None):
        super().__init__(parent)
        self.schluessel, self.name, self.sofort = schluessel, name, sofort
        self._notizen = termine.notizen(schluessel)
        self._weg: set[str] = set()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        self._liste = QVBoxLayout()
        self._liste.setSpacing(6)
        v.addLayout(self._liste)
        self.text = QLineEdit()
        self.text.setPlaceholderText(platzhalter or "Neue Notiz …")
        self.text.returnPressed.connect(self._hinzu)
        v.addWidget(self.text)
        zeile = QHBoxLayout()
        zeile.setSpacing(8)
        self.wv = QCheckBox("Wiedervorlage am")
        self.wv.setToolTip("Erinnert an diesem Tag im Terminkalender (Seite Termine, mit Windows-Benachrichtigung)")
        self.wv_datum = DatumFeld(date.today() + timedelta(days=7))
        self.wv_datum.setEnabled(False)
        self.wv.toggled.connect(self.wv_datum.setEnabled)
        hinzu = knopf("Hinzufügen", "ghost", "plus")
        hinzu.clicked.connect(self._hinzu)
        zeile.addWidget(self.wv)
        zeile.addWidget(self.wv_datum)
        zeile.addStretch()
        zeile.addWidget(hinzu)
        v.addLayout(zeile)
        self._zeigen()

    @property
    def sichtbar(self) -> list[termine.Notiz]:
        return [n for n in self._notizen if n.id not in self._weg]

    def _zeigen(self) -> None:
        leeren(self._liste)
        if not self.sichtbar:
            self._liste.addWidget(label("Noch keine Notizen.", "klein"))
        heute = date.today()
        for n in self.sichtbar:
            zeile = QHBoxLayout()
            zeile.setSpacing(8)
            text = label(f"<span style='color:{theme.T.text_3}'>{n.erstellt:%d.%m.%Y}</span>&nbsp; {escape(n.text)}",
                         umbruch=True)
            text.setTextFormat(Qt.RichText)
            zeile.addWidget(text, 1)
            if n.wiedervorlage:
                p = Pille(f"WV {n.wiedervorlage:%d.%m.%Y}", "knapp" if n.wiedervorlage <= heute else "neutral")
                p.setToolTip("Wiedervorlage – erscheint an diesem Tag unter Termine")
                zeile.addWidget(p, 0, Qt.AlignTop)
            weg = knopf("", "ghost", "loeschen", "Notiz löschen")
            weg.clicked.connect(lambda _=False, n=n: self._loeschen(n))
            zeile.addWidget(weg, 0, Qt.AlignTop)
            self._liste.addLayout(zeile)

    def _hinzu(self) -> None:
        text = self.text.text().strip()
        if not text:
            return
        n = termine.Notiz(self.schluessel, self.name, text, date.today(),
                          self.wv_datum.datum() if self.wv.isChecked() else None)
        if self.sofort:
            termine.notiz_speichern(n)
        self._notizen.insert(0, n)
        self.text.clear()
        self.wv.setChecked(False)
        self._zeigen()
        if self.sofort:
            self.geaendert.emit()

    def _loeschen(self, n: termine.Notiz) -> None:
        if self.sofort and n.id:
            termine.notiz_loeschen(n.id)
            self._notizen.remove(n)
        elif n.id:
            self._weg.add(n.id)
        else:
            self._notizen.remove(n)
        self._zeigen()
        if self.sofort:
            self.geaendert.emit()

    def speichern(self) -> bool:
        """Gepufferte Änderungen schreiben (auch eine nur eingetippte, noch nicht hinzugefügte Notiz).
        Gibt zurück, ob sich etwas geändert hat."""
        if self.text.text().strip():
            self._hinzu()
        if self.sofort:
            return False
        neu = [n for n in self._notizen if not n.id]
        for nid in self._weg:
            termine.notiz_loeschen(nid)
        for n in neu:
            termine.notiz_speichern(n)
        return bool(neu or self._weg)
