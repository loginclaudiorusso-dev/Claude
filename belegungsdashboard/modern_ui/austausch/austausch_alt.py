"""Fenster „Austausch mit dem neuen Programm“ für das alte Programm (1.05). Start: ``Austausch altes Programm.bat``."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import werkzeug as wz  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QFileDialog, QLabel, QMessageBox,  # noqa: E402
                               QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

ak = wz.ak


class Vorschau(QDialog):
    """Was übernommen wird – Konflikte zum Abhaken (ohne Haken bleibt der eigene Stand)."""

    def __init__(self, punkte, meta, eltern=None):
        super().__init__(eltern)
        self.setWindowTitle("Austauschdatei einlesen – Vorschau")
        self.resize(900, 560)
        self.punkte = punkte
        b = ak.bilanz(punkte)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Von {meta.get('von') or '–'} · {str(meta.get('erstellt') or '')[:16].replace('T', ' ')} · "
                             f"Prüfwerte in Ordnung"))
        lay.addWidget(QLabel(f"<b>{b.uebernehmen} werden übernommen · {b.schon_da} schon gleich · "
                             f"{b.konflikt} Konflikt(e)</b>"))
        if b.konflikt:
            hinweis = QLabel("Konflikt = hier seit dem letzten Austausch anders geändert. Haken setzen, um den Eintrag aus "
                             "der Datei zu übernehmen; ohne Haken bleibt Ihr Stand und geht beim nächsten Export zurück.")
            hinweis.setWordWrap(True)
            lay.addWidget(hinweis)
        self.baum = QTreeWidget()
        self.baum.setHeaderLabels(["Eintrag", "Art", "Status"])
        self.baum.setColumnWidth(0, 560)
        self.zeilen = []
        for bereich in ak.BEREICHE:
            xs = [p for p in punkte if p.aenderung.bereich == bereich.name and p.status != "schon_da"]
            if not xs:
                continue
            gruppe = QTreeWidgetItem([f"{bereich.titel} ({len(xs)})"])
            self.baum.addTopLevelItem(gruppe)
            for p in xs:
                x = p.aenderung
                text = ak.beschreibung(x.bereich, x.eintrag if x.eintrag is not None else p.hier, x.schluessel)
                if p.status == "konflikt" and p.hier is not None:
                    text += "\n   hier: " + ak.beschreibung(x.bereich, p.hier, x.schluessel)
                z = QTreeWidgetItem([text, ak.ART_TEXT.get(x.art, x.art), ak.STATUS_TEXT[p.status]])
                if p.status == "konflikt":
                    z.setFlags(z.flags() | Qt.ItemIsUserCheckable)
                    z.setCheckState(0, Qt.Unchecked)
                gruppe.addChild(z)
                self.zeilen.append((z, p))
            gruppe.setExpanded(True)
        lay.addWidget(self.baum)
        knoepfe = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        knoepfe.button(QDialogButtonBox.Ok).setText("Übernehmen")
        knoepfe.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        knoepfe.accepted.connect(self.accept)
        knoepfe.rejected.connect(self.reject)
        lay.addWidget(knoepfe)

    def accept(self):
        for z, p in self.zeilen:
            if p.status == "konflikt":
                p.uebernehmen = z.checkState(0) == Qt.Checked
        super().accept()


class Fenster(QWidget):
    def __init__(self):
        super().__init__()
        self.ordner = wz.datenordner()
        self.setWindowTitle("INNternat – Austausch mit dem neuen Programm")
        self.resize(560, 300)
        lay = QVBoxLayout(self)
        text = QLabel("Ihre Änderungen an Anreisen, Abreisen, Zimmerplanung, Umzügen und Mietverträgen als Datei "
                      "weitergeben – oder die Datei aus dem neuen Programm hier einlesen.<br><br>"
                      "<b>Bitte das alte Programm vor dem Einlesen schließen.</b><br>"
                      f"Datenordner: {self.ordner}")
        text.setWordWrap(True)
        lay.addWidget(text)
        for titel, fn in (("Meine Änderungen exportieren …", lambda: self.export(False)),
                          ("Austauschdatei einlesen …", self.einlesen),
                          ("Ganzen Stand exportieren …", lambda: self.export(True))):
            k = QPushButton(titel)
            k.setMinimumHeight(36)
            k.clicked.connect(fn)
            lay.addWidget(k)

    def export(self, alles: bool):
        roh, name, n, st = wz.export(self.ordner, alles)
        if not n:
            QMessageBox.information(self, "Austausch", "Seit dem letzten Austausch hat sich nichts geändert.")
            return
        ziel, _ = QFileDialog.getSaveFileName(self, "Austauschdatei speichern", str(Path.home() / name),
                                              "Austauschdatei (*.json)")
        if not ziel:
            return
        Path(ziel).write_bytes(roh)
        wz.export_gemerkt(self.ordner, st)
        QMessageBox.information(self, "Austausch", f"{n} Änderung(en) gespeichert:\n{ziel}")

    def einlesen(self):
        quelle, _ = QFileDialog.getOpenFileName(self, "Austauschdatei einlesen", str(Path.home()),
                                                "Austauschdatei (*.json)")
        if not quelle:
            return
        try:
            punkte, meta = wz.pruefen(self.ordner, Path(quelle).read_bytes())
        except ak.AustauschFehler as exc:
            QMessageBox.warning(self, "Austausch", str(exc))
            return
        if not any(p.status != "schon_da" for p in punkte):
            QMessageBox.information(self, "Austausch", "Alles aus der Datei ist hier schon so – nichts zu tun.")
            return
        dlg = Vorschau(punkte, meta, self)
        if dlg.exec() != QDialog.Accepted:
            return
        zahl, sicherung = wz.uebernehmen(self.ordner, punkte)
        QMessageBox.information(self, "Austausch", f"Übernommen: {zahl['neu']} neu, {zahl['geaendert']} geändert, "
                                                   f"{zahl['entfernt']} entfernt.\n\nSicherung vorher: {sicherung}")


def main() -> int:
    app = QApplication(sys.argv)
    f = Fenster()
    f.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
