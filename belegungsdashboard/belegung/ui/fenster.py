"""Mehrere Ansichten gleichzeitig: Zimmerplan-Reiter als eigenes Fenster (z. B. Zeitstrahl neben Zuteilen).

Die Fenster teilen sich den Zustand: Was in einem Fenster gespeichert wird, meldet ``listen_geaendert`` –
alle anderen Fenster (und die Hauptseite) rechnen neu. Importe und die automatische UWT-Zuteilung laufen
nur im Hauptfenster.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

_fenster: list[QWidget] = []


def zimmerplan_fenster(zustand, tab: int = 0) -> QWidget:
    from .seiten.zimmerplan import TABS, ZimmerplanSeite

    w = QWidget(None, Qt.Window)
    w.setObjectName("wurzel")
    w.setAttribute(Qt.WA_DeleteOnClose, True)
    w.setAttribute(Qt.WA_StyledBackground, True)
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 12, 0, 0)
    seite = ZimmerplanSeite(zustand, nebenfenster=True)
    lay.addWidget(seite)
    w.seite = seite
    seite.tabs.setzen(tab)
    seite._tab_anzeigen(tab)
    w.setWindowTitle(f"Zimmerplan – {TABS[tab]}")
    bildschirm = w.screen().availableGeometry() if w.screen() else None
    b, h = 1200, 820
    if bildschirm is not None:
        b, h = min(b, int(bildschirm.width() * 0.9)), min(h, int(bildschirm.height() * 0.9))
    w.resize(b, h)
    _fenster.append(w)
    w.destroyed.connect(lambda *_: _fenster.remove(w) if w in _fenster else None)
    w.show()
    return w
