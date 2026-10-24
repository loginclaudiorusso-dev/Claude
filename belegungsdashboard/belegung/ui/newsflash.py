"""Benachrichtigungen ohne Klick: wechselnde Newsflash-Leiste unter dem Seitenkopf und Popup unten rechts für neue
dringende Meldungen. Inhalt: ``belegung.newsflash``."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import newsflash as nf
from . import icons, theme
from .widgets import KurzLabel, knopf, label

WECHSEL_MS = 7000           # Leiste: alle 7 Sekunden die nächste Meldung
POPUP_MS = 20000            # Popup: schließt nach 20 Sekunden von selbst (nicht, solange die Maus darüber ist)


def _farbe(stufe: str) -> str:
    t = theme.T
    return {"dringend": t.ueber, "bald": t.knapp, "neu": t.accent}.get(stufe, t.text_2)


class NewsflashLeiste(QFrame):
    """Eine Zeile, die alle offenen Meldungen nacheinander zeigt. Klick (optional) öffnet die Meldung."""

    oeffnen = Signal(object)            # Meldung

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("newsflash")
        self.meldungen: list[nf.Meldung] = []
        self.i = 0
        h = QHBoxLayout(self)
        h.setContentsMargins(28, 6, 20, 6)
        h.setSpacing(10)
        self.icon = QLabel()
        h.addWidget(self.icon)
        self.stufe = QLabel()
        h.addWidget(self.stufe)
        self.text = KurzLabel()
        self.text.setCursor(Qt.PointingHandCursor)
        self.text.installEventFilter(self)
        h.addWidget(self.text, 1)
        self.zahl = label("", "klein")
        h.addWidget(self.zahl)
        self.zurueck = knopf("", "icon", "links", "Vorherige Meldung")
        self.zurueck.clicked.connect(lambda: self._schritt(-1))
        self.vor = knopf("", "icon", "rechts", "Nächste Meldung")
        self.vor.clicked.connect(lambda: self._schritt(1))
        h.addWidget(self.zurueck)
        h.addWidget(self.vor)
        self.timer = QTimer(self, interval=WECHSEL_MS, timeout=lambda: self._schritt(1))
        self.setToolTip("Wechselt von selbst · Maus darüber hält an · Klick öffnet")
        self.setzen([])

    def setzen(self, meldungen: list[nf.Meldung]) -> None:
        alt = self.meldungen[self.i].id if self.meldungen and self.i < len(self.meldungen) else None
        self.meldungen = meldungen
        ids = [m.id for m in meldungen]
        self.i = ids.index(alt) if alt in ids else 0
        self._zeigen()
        if len(meldungen) > 1 and not self.underMouse():
            self.timer.start()
        else:
            self.timer.stop()

    def _schritt(self, n: int) -> None:
        if self.meldungen:
            self.i = (self.i + n) % len(self.meldungen)
            self._zeigen()

    def _zeigen(self) -> None:
        t = theme.T
        mehrere = len(self.meldungen) > 1
        self.zurueck.setVisible(mehrere)
        self.vor.setVisible(mehrere)
        if not self.meldungen:
            farbe = t.ok
            self.icon.setPixmap(icons.pixmap("haken", farbe, 16))
            self.stufe.setText("Alles erledigt")
            self.text.setText("Nichts Dringendes und nichts Offenes.")
            self.zahl.setText("")
        else:
            m = self.meldungen[self.i]
            farbe = _farbe(m.stufe)
            self.icon.setPixmap(icons.pixmap("warnung" if m.stufe == "dringend" else "glocke", farbe, 16))
            self.stufe.setText(nf.STUFE_TEXT[m.stufe])
            self.text.setText(m.zeile)
            self.zahl.setText(f"{self.i + 1}/{len(self.meldungen)}")
        self.stufe.setStyleSheet(f"color: {farbe}; font-weight: 700;")
        self.setStyleSheet(f"QFrame#newsflash {{ background: {theme.alpha(farbe, .10)}; "
                           f"border-bottom: 1px solid {theme.alpha(farbe, .35)}; }}")

    def enterEvent(self, e) -> None:
        self.timer.stop()                       # beim Lesen nicht weiterspringen
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        if len(self.meldungen) > 1:
            self.timer.start()
        super().leaveEvent(e)

    def eventFilter(self, obj, e) -> bool:
        if obj is self.text and e.type() == QEvent.MouseButtonRelease and self.meldungen:
            self.oeffnen.emit(self.meldungen[self.i])
            return True
        return super().eventFilter(obj, e)


class MeldungPopup(QFrame):
    """Popup unten rechts: neue dringende Meldungen, je Zeile „Ansehen“. Schließt sich von selbst."""

    oeffnen = Signal(object)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("meldungpopup")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(16, 12, 12, 12)
        self.v.setSpacing(8)
        self.timer = QTimer(self, singleShot=True, timeout=self.hide)
        self.hide()

    def zeigen(self, meldungen: list[nf.Meldung]) -> None:
        t = theme.T
        while self.v.count():
            it = self.v.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
            elif it.layout():
                while it.layout().count():
                    w = it.layout().takeAt(0).widget()
                    if w:
                        w.deleteLater()
        kopf = QHBoxLayout()
        ic = QLabel()
        ic.setPixmap(icons.pixmap("warnung", t.ueber, 18))
        kopf.addWidget(ic)
        kopf.addWidget(label(f"{len(meldungen)} dringend" if len(meldungen) > 1 else "Dringend", "kartentitel"))
        kopf.addStretch()
        zu = knopf("", "icon", "schliessen", "Schließen")
        zu.clicked.connect(self.hide)
        kopf.addWidget(zu)
        self.v.addLayout(kopf)
        for m in meldungen[:4]:
            zeile = QHBoxLayout()
            text = label(m.zeile, umbruch=True)
            text.setMaximumWidth(330)
            zeile.addWidget(text, 1)
            b = knopf("Ansehen", "ghost")
            b.clicked.connect(lambda _c=False, m=m: (self.hide(), self.oeffnen.emit(m)))
            zeile.addWidget(b, 0, Qt.AlignTop)
            self.v.addLayout(zeile)
        if len(meldungen) > 4:
            self.v.addWidget(label(f"… und {len(meldungen) - 4} weitere – oben in der Leiste", "klein"))
        self.setStyleSheet(f"QFrame#meldungpopup {{ background: {t.surface}; border: 1px solid {theme.alpha(t.ueber, .5)}; "
                           f"border-left: 4px solid {t.ueber}; border-radius: 10px; }}")
        self.setFixedWidth(460)
        self.adjustSize()
        p = self.parentWidget()
        self.move(p.width() - self.width() - 24, p.height() - self.height() - 24)
        self.raise_()
        self.show()
        self.timer.start(POPUP_MS)

    def enterEvent(self, e) -> None:
        self.timer.stop()
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self.timer.start(POPUP_MS // 2)
        super().leaveEvent(e)
