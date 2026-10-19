"""Maske „Zimmer zur Reinigung hinzufügen“: ein oder mehrere Zimmer für einen Tag zusätzlich auf die Reinigungsliste
setzen (Zwischen-, Grund-, Sonderreinigung …). Die Logik steht in ``zimmerplan.reinigung_hinzufuegen``."""

from __future__ import annotations

import re
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QCompleter, QDialog, QGridLayout, QHBoxLayout, QLineEdit, QVBoxLayout

from .. import zimmerplan as zp
from .widgets import DatumFeld, Hinweis, knopf, label


def zimmer_lesen(text: str, bekannt: set[str]) -> tuple[list[str], list[str]]:
    """„2-204, 6-403“ / „Haus 2 Zimmer 408“ / „Zimmer 108“ → Zimmer-IDs und Hinweise (wie in der Assistenz)."""
    from .. import assistenz

    ids, rest, hinweise = assistenz._zimmer(text, bekannt)
    # nur die Nummer („204“, „E02“): gilt, wenn es sie in genau einem Haus gibt
    for m in re.finditer(r"(?<![\w.-])([A-Za-z]?\d{2,4})(?![\w.-])", rest):
        passend = sorted(z for z in bekannt if z.rsplit("-", 1)[-1].upper() == m.group(1).upper())
        if len(passend) == 1:
            ids.append(passend[0])
        elif passend:
            hinweise.append(f"„{m.group(1)}“ gibt es in mehreren Häusern ("
                            + ", ".join(z.removeprefix("GS-") for z in passend) + ") – bitte mit Haus, z. B. "
                            f"{passend[0].removeprefix('GS-')}.")
        else:
            hinweise.append(f"Zimmer „{m.group(1)}“ gibt es im Zimmerplan nicht.")
    return list(dict.fromkeys(ids)), hinweise


class ReinigungDialog(QDialog):
    def __init__(self, zustand, zimmer: list[zp.Zimmer], parent=None, vorgabe: str = "", tag: date | None = None):
        super().__init__(parent)
        self.z = zustand
        self.bekannt = {z.id for z in zimmer if z.aktiv}
        self.eingetragen: list[str] = []
        self.setWindowTitle("Zimmer zur Reinigung hinzufügen")
        self.setMinimumWidth(500)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Zimmer zur Reinigung hinzufügen", "seitentitel"))
        v.addWidget(label("Zusätzlich zu Auszug und Vorbereiten – das Zimmer steht dann an diesem Tag auf der "
                          "Reinigungsliste (auch im Wochenblatt, Druck und Excel) und lässt sich dort abhaken.",
                          "muted", umbruch=True))
        r = QGridLayout()
        r.setHorizontalSpacing(12)
        r.setVerticalSpacing(10)
        self.feld = QLineEdit(vorgabe.removeprefix("GS-") if isinstance(vorgabe, str) else "")
        self.feld.setPlaceholderText("z. B. 2-204 oder mehrere: 2-204, 2-205, 6-403 (nur „204“ geht, wenn eindeutig)")
        kurz = sorted((z.kurz for z in zimmer if z.aktiv), key=str)
        vervollst = QCompleter(kurz, self.feld)
        vervollst.setCaseSensitivity(Qt.CaseInsensitive)
        vervollst.setFilterMode(Qt.MatchContains)
        self.feld.setCompleter(vervollst)
        r.addWidget(label("Zimmer", "fett"), 0, 0)
        r.addWidget(self.feld, 0, 1)
        self.tag = DatumFeld(tag or date.today())
        r.addWidget(label("Tag", "fett"), 1, 0)
        r.addWidget(self.tag, 1, 1, Qt.AlignLeft)
        self.grund = QComboBox()
        self.grund.setEditable(True)
        self.grund.addItems(zp.REINIGUNG_GRUENDE)
        r.addWidget(label("Art / Grund", "fett"), 2, 0)
        r.addWidget(self.grund, 2, 1)
        r.setColumnStretch(1, 1)
        v.addLayout(r)
        self.hinweis = Hinweis("", "warnung")
        self.hinweis.setVisible(False)
        v.addWidget(self.hinweis)
        knoepfe = QHBoxLayout()
        knoepfe.addStretch()
        abbrechen = knopf("Abbrechen", "ghost")
        abbrechen.clicked.connect(self.reject)
        ok = knopf("Hinzufügen", "primary", "haken")
        ok.setDefault(True)
        ok.clicked.connect(self._hinzufuegen)
        knoepfe.addWidget(abbrechen)
        knoepfe.addWidget(ok)
        v.addLayout(knoepfe)

    def _hinzufuegen(self) -> None:
        ids, hinweise = zimmer_lesen(self.feld.text(), self.bekannt)
        if not ids or hinweise:
            self.hinweis.text.setText(" ".join(hinweise) or "Bitte mindestens ein Zimmer angeben, z. B. 2-204.")
            self.hinweis.setVisible(True)
            return
        tag, grund = self.tag.datum(), self.grund.currentText()
        for zid in ids:
            zp.reinigung_hinzufuegen(zid, tag, grund)
        self.eingetragen = ids
        self.z.meldung.emit(f"{len(ids)} Zimmer für {tag:%d.%m.%Y} zur Reinigung hinzugefügt ("
                            + ", ".join(i.removeprefix("GS-") for i in ids) + ").", "ok")
        self.z.zimmer_geaendert.emit()
        self.z.termine_geaendert.emit()
        self.accept()
