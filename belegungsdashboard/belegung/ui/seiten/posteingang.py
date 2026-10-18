"""Assistenz: normale Eingaben („6-403 Fliegen beseitigen bis 1.11.26“) verstehen und umsetzen – Kalender, Mängel,
Notizen am Zimmer – und der Posteingang für Mails zu Anmeldungen, Gästehaus, Storno, Abbruch und Hinweisen
(erkennen, Vorschlag prüfen, umsetzen; Abbrüche bleiben mit Prüfliste offen, bis alles abgehakt ist)."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QPlainTextEdit,
    QVBoxLayout, QWidget,
)

from ... import anreiseliste, erinnerung, mails
from ... import zimmerplan as zp
from ..basis import Seite, Zustand, sichtbar
from ..widgets import DatumFeld, Hinweis, Karte, Pille, Segment, Tabelle, knopf, label, leeren

STATUS_STUFE = {"offen": "knapp", "zu prüfen": "kritisch", "erledigt": "ok", "verworfen": "neutral"}


class MailFeld(QPlainTextEdit):
    """Textfeld, das auch .eml-/.txt-Dateien per Ziehen annimmt."""

    def __init__(self, seite: "PosteingangSeite"):
        super().__init__()
        self.seite = seite
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dropEvent(self, e) -> None:
        if e.mimeData().hasUrls():
            self.seite.dateien_laden([Path(u.toLocalFile()) for u in e.mimeData().urls()])
            e.acceptProposedAction()
        else:
            super().dropEvent(e)


class PosteingangSeite(Seite):
    titel = "Assistenz"
    untertitel = "Aufgaben, Termine, Mängel und Mails – einfach eintippen, prüfen, umsetzen"
    zeigt_filter = False
    zeigt_bezug = False
    reiter_attr = "reiter"
    REITER = ["Aufgaben && Notizen", "Mails"]          # „&&“ = ein „&“ (sonst Tastenkürzel)

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.reiter = Segment(self.REITER, 0)
        self.reiter.geaendert.connect(self._tab)
        self.anheften(self.reiter)
        self.w_assistenz = self._assistenz_bauen()
        self.lay.addWidget(self.w_assistenz)
        self.w_mail = QWidget()
        self._mail_lay = QVBoxLayout(self.w_mail)
        self._mail_lay.setContentsMargins(0, 0, 0, 0)
        self._mail_lay.setSpacing(16)
        self.lay.addWidget(self.w_mail)
        self._warteschlange: list[tuple[str, str, str]] = []
        self._erkannt: mails.Erkannt | None = None
        self._treffer: list[mails.Treffer] = []
        self._schritte: list[mails.Schritt] = []
        self._zimmerwahl: QComboBox | None = None
        self._quelle_id: str | None = None          # abgelegter Eingang, der gerade bearbeitet wird

        # ---- 1. Mail einfügen ----------------------------------------------------------------
        ein = Karte("Mail einfügen", "In Outlook die Mail öffnen, Strg+A und Strg+C – hier Strg+V. Oder .eml-Datei "
                                     "hierher ziehen bzw. markierte Mails direkt aus Outlook holen.")
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        self.betreff = QLineEdit()
        self.betreff.setPlaceholderText("Betreff (hilft, z. B. „Stornierung Zimmer …“)")
        self.absender = QLineEdit()
        self.absender.setPlaceholderText("Absender (optional)")
        form.addWidget(label("Betreff", "fett"), 0, 0)
        form.addWidget(self.betreff, 0, 1)
        form.addWidget(label("Von", "fett"), 0, 2)
        form.addWidget(self.absender, 0, 3)
        form.setColumnStretch(1, 3)
        form.setColumnStretch(3, 1)
        ein.inhalt.addLayout(form)
        self.text = MailFeld(self)
        self.text.setPlaceholderText("Mail-Text hier einfügen …")
        self.text.setMinimumHeight(150)
        ein.inhalt.addWidget(self.text)
        zeile = QHBoxLayout()
        erkennen = knopf("Erkennen", "primary", "funke")
        erkennen.clicked.connect(self.erkennen)
        zeile.addWidget(erkennen)
        if erinnerung.outlook_moeglich():
            ol = knopf("Aus Outlook", "ghost", "hochladen", "In Outlook markierte Mails übernehmen (eine nach der anderen)")
            ol.clicked.connect(self._outlook)
            zeile.addWidget(ol)
        datei = knopf("Datei …", "ghost", "datei", ".eml- oder .txt-Datei öffnen")
        datei.clicked.connect(self._datei)
        zeile.addWidget(datei)
        leer = knopf("Leeren", "ghost")
        leer.clicked.connect(self._leeren)
        zeile.addWidget(leer)
        zeile.addStretch()
        self.schlange_info = label("", "klein")
        zeile.addWidget(self.schlange_info)
        self.b_naechste = knopf("Nächste Mail", "ghost", "rechts")
        self.b_naechste.clicked.connect(self._naechste)
        self.b_naechste.setVisible(False)
        zeile.addWidget(self.b_naechste)
        ein.inhalt.addLayout(zeile)
        self._mail_lay.addWidget(ein)

        # ---- 2. Erkannt und Vorschlag ----------------------------------------------------------
        self.erg = Karte("Erkannt", "Bitte prüfen – alles lässt sich ändern. „Neu prüfen“ übernimmt Änderungen.")
        self.erg.setVisible(False)
        raster = QGridLayout()
        raster.setHorizontalSpacing(10)
        raster.setVerticalSpacing(8)
        self.art = QComboBox()
        for k, v in mails.ARTEN.items():
            self.art.addItem(v, k)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Nachname, Vorname")
        self.tn = QLineEdit()
        self.tn.setPlaceholderText("TN-Nr.")
        self.tn.setMaximumWidth(120)
        self.von = DatumFeld(date.today())
        self.bis = DatumFeld(date.today())
        self.von_ok = QCheckBox("Anreise")
        self.bis_ok = QCheckBox("Abreise / letzter Tag")
        self.massnahme = QLineEdit()
        self.massnahme.setPlaceholderText("Maßnahme, z. B. RVL oder Gast Gästehaus")
        raster.addWidget(label("Art", "fett"), 0, 0)
        raster.addWidget(self.art, 0, 1)
        raster.addWidget(label("Name", "fett"), 0, 2)
        raster.addWidget(self.name, 0, 3)
        raster.addWidget(label("TN-Nr.", "fett"), 0, 4)
        raster.addWidget(self.tn, 0, 5)
        raster.addWidget(self.von_ok, 1, 0)
        raster.addWidget(self.von, 1, 1, Qt.AlignLeft)
        raster.addWidget(self.bis_ok, 1, 2)
        raster.addWidget(self.bis, 1, 3, Qt.AlignLeft)
        raster.addWidget(label("Maßnahme", "fett"), 2, 0)
        raster.addWidget(self.massnahme, 2, 1, 1, 3)
        raster.setColumnStretch(3, 1)
        self.erg.inhalt.addLayout(raster)
        neu = knopf("Neu prüfen", "ghost", "aktualisieren", "Geänderte Angaben übernehmen und Vorschlag neu berechnen")
        neu.clicked.connect(lambda: self._auswerten(aus_feldern=True))
        self.erg.aktion(neu)
        self.unsicher = QVBoxLayout()
        self.erg.inhalt.addLayout(self.unsicher)
        z = QHBoxLayout()
        z.addWidget(label("Zugeordnet", "fett"))
        self.zuordnung = QComboBox()
        self.zuordnung.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.zuordnung.setMinimumContentsLength(30)
        self.zuordnung.currentIndexChanged.connect(lambda _i: self._vorschlag_zeigen())
        z.addWidget(self.zuordnung, 1)
        self.erg.inhalt.addLayout(z)
        self.erg.inhalt.addWidget(label("Vorschlag", "abschnitt"))
        self.schritte_lay = QVBoxLayout()
        self.schritte_lay.setSpacing(6)
        self.erg.inhalt.addLayout(self.schritte_lay)
        knoepfe = QHBoxLayout()
        umsetzen = knopf("Umsetzen", "primary", "haken", "Angehakte Schritte ausführen und die Mail ablegen")
        umsetzen.clicked.connect(self._umsetzen)
        ablegen = knopf("Nur ablegen", "ghost", None, "Ohne Aktion als „offen“ ablegen – später bearbeiten")
        ablegen.clicked.connect(lambda: self._ablegen("offen"))
        verwerfen = knopf("Verwerfen", "ghost", None, "Nicht relevant – als „verworfen“ ablegen")
        verwerfen.clicked.connect(lambda: self._ablegen("verworfen"))
        for b in (umsetzen, ablegen, verwerfen):
            knoepfe.addWidget(b)
        knoepfe.addStretch()
        self.erg.inhalt.addLayout(knoepfe)
        self._mail_lay.addWidget(self.erg)

        # ---- 3. Eingänge ---------------------------------------------------------------------
        liste = Karte("Eingänge", "Umgesetzte und abgelegte Mails. Abbrüche bleiben „zu prüfen“, bis die Prüfliste "
                                  "abgehakt ist – Doppelklick öffnet.")
        self.filter = Segment(["Offen und zu prüfen", "Alle"], 0)
        self.filter.geaendert.connect(lambda _i: self._liste_zeigen())
        liste.aktion(self.filter)
        self.tab = Tabelle(["Eingang", "Art", "Person", "Zeitraum", "Status", "Noch offen"],
                           ["l", "l", "l", "l", "l", "l"], dehnen=5)
        self.tab.setTextElideMode(Qt.ElideRight)
        self.tab.doubleClicked.connect(lambda i: self._eingang_oeffnen(self.tab.daten_zeile(i.row())))
        liste.inhalt.addWidget(self.tab)
        self.leer = label("Noch keine Mails.", "muted")
        liste.inhalt.addWidget(self.leer)
        self._mail_lay.addWidget(liste)
        self.lay.addStretch()
        self._tab(0)
        for s in (zustand.listen_geaendert, zustand.zimmer_geaendert):
            s.connect(self.anstossen)

    # ---- läuft ohne Pivot-Daten --------------------------------------------------------------

    def anstossen(self) -> None:
        self._veraltet = True
        if sichtbar(self):
            self._ausfuehren()

    def showEvent(self, e):
        QWidget.showEvent(self, e)
        if self._veraltet:
            self._ausfuehren()

    def aktualisieren(self) -> None:
        self._liste_zeigen()
        self._verlauf_zeigen()

    def _tab(self, i: int) -> None:
        self.w_assistenz.setVisible(i == 0)
        self.w_mail.setVisible(i == 1)
        if i == 0:
            self.eingabe.setFocus()

    # ================================================================== Assistenz (Aufgaben & Notizen)

    def _assistenz_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        k = Karte("Was ist zu tun?", "Ganz normal eintippen – eine Zeile je Auftrag. Zimmer, Datum und Mangel werden "
                                     "erkannt; vor dem Ausführen sehen Sie alles und können abwählen.")
        self.eingabe = QPlainTextEdit()
        self.eingabe.setPlaceholderText("z. B.  6-403 Fliegen beseitigen bis 1.11.26\n"
                                        "        3.1-E02 Rollo defekt\n"
                                        "        2-115 Heizung erledigt\n"
                                        "        Freitag 10 Uhr Teambesprechung")
        self.eingabe.setFixedHeight(104)
        self.eingabe.installEventFilter(self)
        k.inhalt.addWidget(self.eingabe)
        z = QHBoxLayout()
        verstehen = knopf("Verstehen", "primary", "funke", "Eingabe auswerten (Strg+Enter)")
        verstehen.clicked.connect(self._verstehen)
        z.addWidget(verstehen)
        z.addWidget(label("Strg+Enter · „bis …“ = Frist, „am …“/„morgen“/„Freitag“ = Termin · „erledigt“ hakt ab",
                          "klein"))
        z.addStretch()
        k.inhalt.addLayout(z)
        v.addWidget(k)

        self.k_vorschau = Karte("Verstanden", "Häkchen entfernen, was nicht passieren soll – dann „Ausführen“.")
        self.vorschau_lay = QVBoxLayout()
        self.vorschau_lay.setSpacing(10)
        self.k_vorschau.inhalt.addLayout(self.vorschau_lay)
        kz = QHBoxLayout()
        self.b_ausfuehren = knopf("Ausführen", "primary", "haken")
        self.b_ausfuehren.clicked.connect(self._ausfuehren_assistenz)
        kz.addWidget(self.b_ausfuehren)
        verwerfen = knopf("Verwerfen", "ghost")
        verwerfen.clicked.connect(lambda: (self.k_vorschau.setVisible(False), setattr(self, "_verstanden", [])))
        kz.addWidget(verwerfen)
        kz.addStretch()
        self.k_vorschau.inhalt.addLayout(kz)
        self.k_vorschau.setVisible(False)
        v.addWidget(self.k_vorschau)

        kv = Karte("Zuletzt erledigt", "Was die Assistenz eingetragen hat – „Rückgängig“ nimmt einen Auftrag ganz zurück.")
        self.verlauf_tab = Tabelle(["Wann", "Eingabe", "Eingetragen", "Aktion"], ["l", "l", "l", "l"], dehnen=2)
        kv.inhalt.addWidget(self.verlauf_tab)
        v.addWidget(kv)
        self._verstanden: list = []
        return w

    def eventFilter(self, obj, e) -> bool:
        from PySide6.QtCore import QEvent

        if obj is getattr(self, "eingabe", None) and e.type() == QEvent.KeyPress and \
                e.key() in (Qt.Key_Return, Qt.Key_Enter) and e.modifiers() & Qt.ControlModifier:
            self._verstehen()
            return True
        return super().eventFilter(obj, e)

    def _verstehen(self) -> None:
        from ... import assistenz

        zeilen = [z.strip() for z in self.eingabe.toPlainText().splitlines() if z.strip()]
        if not zeilen:
            return
        bekannt = {z.id for z in zp.laden().zimmer}
        self._verstanden = [assistenz.verstehen(z, bekannt) for z in zeilen]
        leeren(self.vorschau_lay)
        for v in self._verstanden:
            box = QVBoxLayout()
            box.setSpacing(4)
            teile = [f"<b>{v.eingabe}</b>"]
            if v.zimmer:
                teile.append("Zimmer " + ", ".join(zid.removeprefix("GS-") for zid in v.zimmer))
            if v.datum:
                teile.append(("Frist " if v.frist else "Termin ") + f"{v.datum:%d.%m.%Y}" + (f" {v.uhrzeit} Uhr" if v.uhrzeit else ""))
            if v.erledigt:
                teile.append("erledigt")
            kopf = label(" · ".join(teile), umbruch=True)
            kopf.setTextFormat(Qt.RichText)
            box.addWidget(kopf)
            for h in v.hinweise:
                box.addWidget(Hinweis(h, "warnung"))
            for a in v.aktionen:
                cb = QCheckBox(a.text)
                cb.setChecked(a.an)
                cb.toggled.connect(lambda an, a=a: setattr(a, "an", an))
                box.addWidget(cb)
            self.vorschau_lay.addLayout(box)
        self.b_ausfuehren.setEnabled(any(v.aktionen for v in self._verstanden))
        self.k_vorschau.setVisible(True)

    def _ausfuehren_assistenz(self) -> None:
        from ... import assistenz

        if not self._verstanden:
            return
        e = assistenz.ausfuehren(self._verstanden)
        self._verstanden = []
        self.k_vorschau.setVisible(False)
        self.eingabe.clear()
        self.z.meldung.emit(f"{len(e['erledigt'])} Schritte eingetragen (Kalender, Mängel, Notizen) – "
                            "„Rückgängig“ unter „Zuletzt erledigt“.", "ok")
        self.z.zimmer_geaendert.emit()           # lädt auch diese Seite neu (Verlauf)
        self.z.termine_geaendert.emit()

    def _verlauf_zeigen(self) -> None:
        from ... import assistenz

        zeilen = []
        for e in assistenz.verlauf()[:30]:
            if e.get("zurueck"):
                knopf_ = label("zurückgenommen", "klein")
            else:
                knopf_ = knopf("Rückgängig", "ghost")
                knopf_.clicked.connect(lambda _c=False, i=e["id"]: self._rueckgaengig(i))
            zeilen.append([datetime.fromisoformat(e["zeit"]).strftime("%d.%m. %H:%M"), " / ".join(e["eingaben"]),
                           " · ".join(e["erledigt"]) or "–", knopf_])
        self.verlauf_tab.setRowCount(0)          # alte Knöpfe sicher entfernen (sonst liegen zwei übereinander)
        self.verlauf_tab.fuellen(zeilen)
        self.verlauf_tab.widgets_einpassen()
        self.verlauf_tab.hoehe_anpassen(8)

    def _rueckgaengig(self, eintrag_id: str) -> None:
        from ... import assistenz

        n = assistenz.rueckgaengig(eintrag_id)
        self.z.meldung.emit(f"Zurückgenommen ({n} Schritte).", "ok")
        self.z.zimmer_geaendert.emit()
        self.z.termine_geaendert.emit()

    # ---- Eingabe -----------------------------------------------------------------------------

    def _leeren(self) -> None:
        self.betreff.clear()
        self.absender.clear()
        self.text.clear()
        self.erg.setVisible(False)
        self._erkannt = None

    def dateien_laden(self, pfade: list[Path]) -> None:
        mails_neu = []
        for p in pfade:
            try:
                if p.suffix.lower() == ".eml":
                    mails_neu.append(mails.eml_lesen(p))
                elif p.suffix.lower() in (".txt", ".text"):
                    mails_neu.append((p.stem, "", p.read_text(encoding="utf-8", errors="replace")))
                elif p.suffix.lower() == ".msg":
                    self.z.meldung.emit(".msg-Dateien kann das Programm nicht lesen – bitte „Aus Outlook“ nutzen oder "
                                        "den Text kopieren.", "warnung")
            except OSError as exc:
                self.z.meldung.emit(f"{p.name} konnte nicht gelesen werden: {exc}", "fehler")
        self._schlange(mails_neu)

    def _datei(self) -> None:
        pfade, _ = QFileDialog.getOpenFileNames(self, "Mail-Dateien öffnen", "", "Mails (*.eml *.txt)")
        if pfade:
            self.dateien_laden([Path(p) for p in pfade])

    def _outlook(self) -> None:
        try:
            auswahl = mails.outlook_auswahl()
        except Exception as exc:                 # noqa: BLE001 – Outlook nicht erreichbar
            self.z.meldung.emit(f"Outlook nicht erreichbar ({exc}). Bitte den Mail-Text kopieren.", "warnung")
            return
        if not auswahl:
            self.z.meldung.emit("In Outlook ist keine Mail markiert.", "warnung")
        self._schlange(auswahl)

    def _schlange(self, neu: list[tuple[str, str, str]]) -> None:
        self._warteschlange = list(neu)
        self._naechste()

    def _naechste(self) -> None:
        if not self._warteschlange:
            self.b_naechste.setVisible(False)
            self.schlange_info.setText("")
            return
        b, a, t = self._warteschlange.pop(0)
        self.betreff.setText(b)
        self.absender.setText(a)
        self.text.setPlainText(t)
        rest = len(self._warteschlange)
        self.schlange_info.setText(f"noch {rest} weitere Mail{'s' if rest != 1 else ''}" if rest else "")
        self.b_naechste.setVisible(bool(rest))
        self.erkennen()

    # ---- Erkennen und Vorschlag -------------------------------------------------------------------

    def erkennen(self) -> None:
        if not (self.text.toPlainText().strip() or self.betreff.text().strip()):
            self.z.meldung.emit("Bitte zuerst den Text einer Mail einfügen.", "warnung")
            return
        self._erkannt = mails.erkennen(self.betreff.text(), self.text.toPlainText())
        e = self._erkannt
        self.art.setCurrentIndex(max(0, self.art.findData(e.art)))
        self.name.setText(e.name)
        self.tn.setText(e.tn_id)
        self.von_ok.setChecked(e.von is not None)
        self.bis_ok.setChecked(e.bis is not None)
        self.von.setzen(e.von or date.today())
        self.bis.setzen(e.bis or e.von or date.today())
        self.massnahme.setText(e.massnahme)
        self._auswerten()

    def _auswerten(self, aus_feldern: bool = False) -> None:
        if self._erkannt is None:
            self.erkennen()
            return
        e = self._erkannt
        if aus_feldern:
            e.art = self.art.currentData()
            e.name = self.name.text().strip()
            e.tn_id = self.tn.text().strip()
            e.von = self.von.datum() if self.von_ok.isChecked() else None
            e.bis = self.bis.datum() if self.bis_ok.isChecked() else None
            e.massnahme = self.massnahme.text().strip()
            if e.art == "gast" and not e.massnahme:
                e.massnahme = "Gast Gästehaus"
            e.unsicher = []
        self.stand = zp.laden()
        personen, _ = anreiseliste.laden()
        self._treffer = mails.zuordnen(e, self.stand, personen)
        self.zuordnung.blockSignals(True)
        self.zuordnung.clear()
        self.zuordnung.addItem("– keine (neue Person) –" if e.art in ("gast", "anmeldung") else "– keine –", None)
        for t in self._treffer[:8]:
            self.zuordnung.addItem(t.text, t.schluessel)
        self.zuordnung.setCurrentIndex(1 if self._treffer else 0)
        self.zuordnung.blockSignals(False)
        leeren(self.unsicher)
        for u in e.unsicher:
            self.unsicher.addWidget(Hinweis(u, "warnung"))
        if not self._treffer and e.art in ("storno", "abbruch", "hinweis") and (e.name or e.tn_id):
            self.unsicher.addWidget(Hinweis("Keine passende Person gefunden – Namen anpassen und „Neu prüfen“, oder "
                                            "im Belegungssystem nachsehen.", "info"))
        self.erg.setVisible(True)
        self._vorschlag_zeigen()

    def _treffer_gewaehlt(self) -> mails.Treffer | None:
        s = self.zuordnung.currentData()
        return next((t for t in self._treffer if t.schluessel == s), None)

    def _vorschlag_zeigen(self) -> None:
        if self._erkannt is None:
            return
        leeren(self.schritte_lay)
        self._zimmerwahl = None
        self._schritte = mails.vorschlag(self._erkannt, self._treffer_gewaehlt(), self.stand)
        if not self._schritte:
            self.schritte_lay.addWidget(label("Nichts zu tun – nur ablegen.", "muted"))
        for s in self._schritte:
            zeile = QHBoxLayout()
            cb = QCheckBox(s.text)
            cb.setChecked(s.an)
            cb.toggled.connect(lambda an, s=s: setattr(s, "an", an))
            zeile.addWidget(cb, 1)
            if s.art == "zimmer" and s.daten.get("person"):
                box = self._zimmer_auswahl(s)
                if box is not None:
                    zeile.addWidget(box)
            self.schritte_lay.addLayout(zeile)

    def _zimmer_auswahl(self, s: mails.Schritt) -> QComboBox | None:
        """Zimmer des Vorschlags ändern – gleiche Auswahl wie beim Zuteilen."""
        from ..zimmerkarte import zimmer_auswahl

        p = next((anreiseliste.Person.aus_dict(x.daten["person"]) for x in self._schritte if x.art == "person_anlegen"),
                 None)
        bedarf = zp.bedarf_aus_personen([p]) if p is not None else \
            [b for b in self.stand.bedarf if b.schluessel == s.daten["person"]]
        if not bedarf:
            return None
        zt = zp.vorschlagen(self.stand.lage, bedarf[:1])[0]
        wahl = zp.ZimmerWahl(bedarf[0], geplant=s.daten.get("zimmer", ""), alternativen=zt.alternativen,
                             ausnahmen=[(z, zp.ausnahme_grund(self.stand.lage, z, bedarf[0])) for z in zt.ausnahmen])
        box = zimmer_auswahl(wahl, self.stand)
        box.currentIndexChanged.connect(lambda _i, s=s, box=box: s.daten.__setitem__("zimmer", box.currentData() or ""))
        self._zimmerwahl = box
        return box

    def _umsetzen(self) -> None:
        if self._erkannt is None:
            return
        angehakt = [s for s in self._schritte if s.an]
        if angehakt and QMessageBox.question(
                self, "Umsetzen", "Folgendes ausführen?\n\n• " + "\n• ".join(s.text for s in angehakt)) != QMessageBox.Yes:
            return
        x = mails.umsetzen(self._erkannt, self._schritte, self.stand, self.betreff.text(), self.text.toPlainText(),
                           self.absender.text(), self._treffer_gewaehlt())
        self.z.meldung.emit(f"{mails.ARTEN[x.art]} umgesetzt: {x.name or 'ohne Person'}"
                            + (" – Prüfliste offen." if x.status == "zu prüfen" else "."), "ok")
        self._fertig()

    def _ablegen(self, status: str) -> None:
        if self._erkannt is None:
            self._erkannt = mails.erkennen(self.betreff.text(), self.text.toPlainText())
        mails.ablegen(self._erkannt, self.betreff.text(), self.text.toPlainText(), self.absender.text(), status)
        self.z.meldung.emit("Mail abgelegt." if status == "offen" else "Mail verworfen.", "ok")
        self._fertig()

    def _fertig(self) -> None:
        if self._quelle_id:                          # bearbeiteter alter Eingang ist durch den neuen ersetzt
            mails.eingang_entfernen(self._quelle_id)
            self._quelle_id = None
        self._leeren()
        self.z.listen_geaendert.emit()
        self.z.zimmer_geaendert.emit()
        self.z.termine_geaendert.emit()
        self._liste_zeigen()
        if self._warteschlange:
            self._naechste()

    # ---- Eingänge ----------------------------------------------------------------------------

    def _liste_zeigen(self) -> None:
        alle = mails.eingaenge()
        self._eingaenge = alle if self.filter.index() == 1 else [x for x in alle if x.status in ("offen", "zu prüfen")]
        zeilen = []
        for x in self._eingaenge:
            zeit = " – ".join(date.fromisoformat(d).strftime("%d.%m.%Y") for d in (x.von, x.bis) if d)
            zeilen.append([datetime.fromisoformat(x.eingang).strftime("%d.%m. %H:%M"), mails.ARTEN.get(x.art, x.art),
                           x.name, zeit, x.status, ", ".join(x.offen_zu_pruefen)])
        self.tab.fuellen(zeilen)
        self.tab.hoehe_anpassen(min(len(zeilen), 12))
        self.tab.setVisible(bool(zeilen))
        self.leer.setVisible(not zeilen)
        self.leer.setText("Nichts offen." if alle else "Noch keine Mails.")

    def _eingang_oeffnen(self, r: int) -> None:
        if 0 <= r < len(self._eingaenge):
            EingangDialog(self, self._eingaenge[r]).exec()
            self._liste_zeigen()
            self.z.termine_geaendert.emit()


class EingangDialog(QDialog):
    """Ein abgelegter Eingang: Text, umgesetzte Schritte, Prüfliste zum Abhaken."""

    def __init__(self, seite: PosteingangSeite, x: mails.Eingang):
        super().__init__(seite)
        self.seite, self.x = seite, x
        self.setWindowTitle(f"{mails.ARTEN.get(x.art, x.art)} – {x.name}")
        v = QVBoxLayout(self)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(10)
        kopf = QHBoxLayout()
        kopf.addWidget(label(f"{mails.ARTEN.get(x.art, x.art)}: {x.name or '–'}", "seitentitel"))
        kopf.addStretch()
        kopf.addWidget(Pille(x.status, STATUS_STUFE.get(x.status, "neutral")))
        v.addLayout(kopf)
        v.addWidget(label(f"Eingang {datetime.fromisoformat(x.eingang):%d.%m.%Y %H:%M}"
                          + (f" · von {x.absender}" if x.absender else "") + (f" · {x.betreff}" if x.betreff else ""),
                          "muted", umbruch=True))
        if x.erledigt:
            v.addWidget(label("Umgesetzt", "abschnitt"))
            for t in x.erledigt:
                v.addWidget(label(f"✓ {t}", umbruch=True))
        self._pruef = []
        if x.pruefliste:
            v.addWidget(label("Prüfliste", "abschnitt"))
            for punkt, an in x.pruefliste.items():
                cb = QCheckBox(punkt)
                cb.setChecked(an)
                cb.toggled.connect(lambda wert, p=punkt: self._haken(p, wert))
                v.addWidget(cb)
        if x.text:
            v.addWidget(label("Mail", "abschnitt"))
            t = QPlainTextEdit(x.text)
            t.setReadOnly(True)
            t.setMinimumHeight(140)
            v.addWidget(t)
        unten = QHBoxLayout()
        if x.status == "offen":
            bearbeiten = knopf("Jetzt bearbeiten", "primary", None, "Mail oben einsetzen und erkennen lassen")
            bearbeiten.clicked.connect(self._bearbeiten)
            unten.addWidget(bearbeiten)
        if x.status in ("offen", "zu prüfen"):
            fertig = knopf("Als erledigt markieren", "ghost", "haken")
            fertig.clicked.connect(lambda: self._status("erledigt"))
            unten.addWidget(fertig)
        else:
            wieder = knopf("Wieder öffnen", "ghost")
            wieder.clicked.connect(lambda: self._status("zu prüfen" if x.pruefliste else "offen"))
            unten.addWidget(wieder)
        unten.addStretch()
        zu = knopf("Schließen", "ghost")
        zu.clicked.connect(self.accept)
        unten.addWidget(zu)
        v.addLayout(unten)
        from ..dialoge import scrollbar_machen

        scrollbar_machen(self, 640, 640)

    def _haken(self, punkt: str, an: bool) -> None:
        self.x = mails.eingang_pruefen(self.x, punkt, an)

    def _status(self, status: str) -> None:
        self.x.status = status
        mails.eingang_speichern(self.x)
        self.accept()

    def _bearbeiten(self) -> None:
        s = self.seite
        s.betreff.setText(self.x.betreff)
        s.absender.setText(self.x.absender)
        s.text.setPlainText(self.x.text)
        s._quelle_id = self.x.id                   # wird beim Umsetzen/Ablegen durch den neuen Eingang ersetzt
        self.accept()
        s.erkennen()
