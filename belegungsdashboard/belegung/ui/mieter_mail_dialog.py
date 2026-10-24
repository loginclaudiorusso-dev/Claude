"""Maske „Mail zum Vertragsende“: vorgefertigte Mail an den Mieter (Verlängerung anfragen oder Auszug bestätigen),
änderbar, dann in Outlook öffnen und dort von Hand abschicken. Texte: ``mieter.ende_mail``."""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QDialog, QGridLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QVBoxLayout

from .. import erinnerung
from .. import mieter as mt
from .widgets import Segment, knopf, label


class MieterMailDialog(QDialog):
    def __init__(self, zustand, mv: mt.Mietvertrag, parent=None):
        super().__init__(parent)
        self.z, self.mv = zustand, mv
        self.arten = list(mt.MAIL_ARTEN)
        self.setWindowTitle("Mail zum Vertragsende")
        self.setMinimumSize(720, 620)
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)
        v.addWidget(label("Mail zum Vertragsende", "seitentitel"))
        wer = f"{mv.vorname} {mv.nachname}".strip()
        v.addWidget(label(f"{wer} · Zimmer {mv.zimmer_kurz} · Ende {mv.bis:%d.%m.%Y}"
                          + (f" · MV {mv.nr}" if mv.nr else " · ohne Vertrag im Programm (laut Gebäudeplan)")
                          + ". Text prüfen und anpassen – Outlook öffnet die Mail, abgeschickt wird dort von Hand.",
                          "muted", umbruch=True))
        self.art = Segment([mt.MAIL_ARTEN[a] for a in self.arten], 0)
        self.art.geaendert.connect(lambda _i: self._text_setzen())
        v.addWidget(self.art)
        r = QGridLayout()
        r.setHorizontalSpacing(12)
        r.setVerticalSpacing(8)
        self.an = QLineEdit(mv.email)
        self.an.setPlaceholderText("E-Mail-Adresse des Mieters (wird am Vertrag gemerkt)")
        r.addWidget(label("An", "fett"), 0, 0)
        r.addWidget(self.an, 0, 1)
        self.betreff = QLineEdit()
        r.addWidget(label("Betreff", "fett"), 1, 0)
        r.addWidget(self.betreff, 1, 1)
        v.addLayout(r)
        self.text = QPlainTextEdit()
        v.addWidget(self.text, 1)
        self.info = label("", "klein", umbruch=True)
        v.addWidget(self.info)
        knoepfe = QHBoxLayout()
        kopieren = knopf("Text kopieren", "ghost", None, "Betreff und Text in die Zwischenablage")
        kopieren.clicked.connect(self._kopieren)
        knoepfe.addWidget(kopieren)
        knoepfe.addStretch()
        schliessen = knopf("Schließen", "ghost")
        schliessen.clicked.connect(self.reject)
        knoepfe.addWidget(schliessen)
        if erinnerung.outlook_moeglich():
            andere = knopf("Anderes Mail-Programm", "ghost", None, "Über das Standard-Mailprogramm öffnen (mailto)")
            andere.clicked.connect(self._mailto)
            knoepfe.addWidget(andere)
            ol = knopf("In Outlook öffnen", "primary", "senden", "Outlook zeigt die fertige Mail – dort prüfen und senden")
            ol.clicked.connect(self._outlook)
            knoepfe.addWidget(ol)
        else:
            m = knopf("Im Mail-Programm öffnen", "primary", "senden", "Öffnet das Standard-Mailprogramm (z. B. Outlook)")
            m.clicked.connect(self._mailto)
            knoepfe.addWidget(m)
        v.addLayout(knoepfe)
        self._text_setzen()

    def _text_setzen(self) -> None:
        betreff, text = mt.ende_mail(self.mv, self.arten[self.art.index()])
        self.betreff.setText(betreff)
        self.text.setPlainText(text)

    def _werte(self) -> tuple[str, str, str]:
        return self.an.text().strip(), self.betreff.text().strip(), self.text.toPlainText()

    def _kopieren(self) -> None:
        _an, betreff, text = self._werte()
        QGuiApplication.clipboard().setText(f"Betreff: {betreff}\n\n{text}")
        self.z.meldung.emit("Betreff und Text kopiert.", "ok")

    def _vermerken(self) -> None:
        if self.mv.nr:
            mt.mail_vermerken(self.mv.nr, self.an.text())
        self.z.zimmer_geaendert.emit()           # Mieter-Seite und „Heute“ aktualisieren

    def _outlook(self) -> None:
        an, betreff, text = self._werte()
        try:
            erinnerung.outlook_entwurf(an, betreff, text)
        except Exception as exc:                 # noqa: BLE001 – Outlook nicht erreichbar: auf mailto ausweichen
            self.info.setText(f"Outlook ließ sich nicht öffnen ({exc}) – es wird das Standard-Mailprogramm versucht.")
            self._mailto()
            return
        self._vermerken()
        self.z.meldung.emit("Mail in Outlook geöffnet – bitte dort prüfen und senden.", "ok")
        self.accept()

    def _mailto(self) -> None:
        an, betreff, text = self._werte()
        if not QDesktopServices.openUrl(QUrl(erinnerung.mailto(an, betreff, text))):
            self.info.setText("Kein Mail-Programm gefunden – „Text kopieren“ und in Outlook einfügen.")
            return
        self._vermerken()
        self.z.meldung.emit("Mail im Mail-Programm geöffnet – bitte dort prüfen und senden.", "ok")
        self.accept()
