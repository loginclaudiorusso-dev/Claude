"""Daten & Import: Pivot-Quelle, Kapazitäten, Anreisen Goslar, Mieten, UWT, manuelle Einträge."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QSpinBox, QVBoxLayout, QWidget,
)

from ... import anreiseliste, erinnerung, importe, laden, speicher, uwt
from ... import zimmerplan as zp
from ...konfig import MANUELLE_KATEGORIEN, STANDORT_LABEL, STANDORTE
from ..basis import Seite, Zustand
from ..widgets import DatumFeld, FlowLayout, Karte, Leer, Pille, Segment, Tabelle, knopf, label, leeren, zahl


class DatenSeite(Seite):
    titel = "Daten & Import"
    untertitel = "Quelle, Kapazitäten und Listen pflegen"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        # Quelle
        self.quelle_karte = Karte("Pivot-Quelle", "Tägliche Reha-Belegung je Haus aus dem Rios-Cube")
        self.quelle_text = label("", "muted", umbruch=True)
        self.quelle_karte.inhalt.addWidget(self.quelle_text)
        knoepfe_w = QWidget()
        knoepfe = FlowLayout(knoepfe_w, abstand=8)
        b_datei = knopf("Andere Datei wählen", None, "datei")
        b_datei.clicked.connect(lambda: self.window().datei_waehlen())
        b_profil = knopf("Pivot-Struktur …", "ghost", "tabelle", "Für Dateien mit abweichendem Aufbau")
        b_profil.clicked.connect(self._profil)
        b_neu = knopf("Neu einlesen", "ghost", "aktualisieren")
        b_neu.clicked.connect(lambda: self.z.neu_laden.emit(False))
        self.b_server = knopf("Vom Server abrufen", "ghost", "server", "OLAP-Refresh über Excel (nur Windows, Netz/VPN nötig)")
        self.b_server.clicked.connect(lambda: self.z.neu_laden.emit(True))
        self.b_server.setEnabled(laden.refresh_moeglich())
        for b in (b_datei, b_profil, b_neu, self.b_server):
            knoepfe.addWidget(b)
        self.quelle_karte.inhalt.addWidget(knoepfe_w)

        # Kapazitäten
        self.kap_karte = Karte("Kapazitäten", "Netto = Reha und Verträge · Brutto = zusätzlich FRAI, Jugendhilfe, andere Bereiche")
        gitter = QGridLayout()
        gitter.setHorizontalSpacing(14)
        gitter.setVerticalSpacing(8)
        gitter.addWidget(label("Netto", "klein"), 0, 1)
        gitter.addWidget(label("Brutto", "klein"), 0, 2)
        self.kap_felder: dict[str, tuple[QSpinBox, QSpinBox]] = {}
        for i, s in enumerate(STANDORTE, start=1):
            gitter.addWidget(label(STANDORT_LABEL[s], "fett"), i, 0)
            n, b = QSpinBox(), QSpinBox()
            for f in (n, b):
                f.setRange(0, 5000)
                f.setFixedWidth(96)
            gitter.addWidget(n, i, 1)
            gitter.addWidget(b, i, 2)
            self.kap_felder[s] = (n, b)
        gitter.setColumnStretch(3, 1)
        self.kap_karte.inhalt.addLayout(gitter)
        speichern = knopf("Kapazitäten speichern", "primary", "haken")
        speichern.clicked.connect(self._kap_speichern)
        self.kap_karte.inhalt.addWidget(speichern, 0)

        # Anreisen Goslar
        self.anr_karte = Karte("Anreisen Internat Goslar",
                               "Anreiselisten (Excel) hochladen – Datum aus dem Titel, gezählt werden Personen mit Internat. "
                               "Abreise, Erinnerung, Geschlecht, Tier und Bemerkungen per Doppelklick bzw. Stift.")
        anr_knoepfe = QHBoxLayout()
        anr_knoepfe.setSpacing(8)
        plus_person = knopf("Person hinzufügen", "ghost", "plus")
        plus_person.clicked.connect(lambda: self._person(None))
        hoch = knopf("Anreiselisten hochladen", "primary", "hochladen")
        hoch.clicked.connect(self._anreiselisten)
        anr_knoepfe.addWidget(plus_person)
        anr_knoepfe.addWidget(hoch)
        anr_kopf = QWidget()
        anr_kopf.setLayout(anr_knoepfe)
        anr_knoepfe.setContentsMargins(0, 0, 0, 0)
        self.anr_karte.aktion(anr_kopf)
        filter_zeile = QHBoxLayout()
        self.anr_filter = Segment(["Kommende", "Ohne Abreise", "Mit Erinnerung", "Alle"], 0)
        self.anr_filter.geaendert.connect(lambda _i: self._anreisen_anzeigen())
        filter_zeile.addWidget(self.anr_filter)
        filter_zeile.addStretch()
        self.anr_info = label("", "klein", umbruch=True)
        filter_zeile.addWidget(label("Ohne Abreise zählen", "klein"))
        self.anr_wochen = QSpinBox()
        self.anr_wochen.setRange(0, 104)
        self.anr_wochen.setSuffix(" Wochen")
        self.anr_wochen.setSpecialValueText("nur als Termin")
        self.anr_wochen.setFixedWidth(130)
        self.anr_wochen.setToolTip("Personen ohne eingetragene Abreise: angenommene Aufenthaltsdauer für Belegung und Prognose")
        self.anr_wochen.setValue(int(speicher.einstellungen().get("anreise_standard_wochen", 0) or 0))
        self.anr_wochen.editingFinished.connect(self._wochen_speichern)
        filter_zeile.addWidget(self.anr_wochen)
        self.anr_karte.inhalt.addLayout(filter_zeile)
        self.anr_karte.inhalt.addWidget(self.anr_info)
        self.anr_tabelle = Tabelle(["Anreise", "Name", "Maßnahme", "Internat", "Abreise", "Erinnerung", ""],
                                   ["l", "l", "l", "l", "l", "l", "l"], dehnen=1)
        self.anr_tabelle.cellDoubleClicked.connect(lambda r, _c: self._person(self._anr_zeilen[r]) if r < len(self._anr_zeilen) else None)
        self.anr_karte.inhalt.addWidget(self.anr_tabelle)
        self.anr_leer = Leer("hochladen", "Noch keine Anreisen",
                             "Eine oder mehrere Anreiselisten wählen (z. B. „Anreiseliste 21-10-2026.xlsx“). Erneutes "
                             "Hochladen aktualisiert die Liste, eingetragene Abreisen bleiben erhalten.")
        self.anr_karte.inhalt.addWidget(self.anr_leer)
        self._anr_zeilen: list = []

        # Mieten (allgemeiner Listen-Import) und UWT
        self.import_karten: dict[str, tuple[Karte, object]] = {}
        karte = Karte("Mieten", "Mietverträge (Von, Bis, Standort, Plätze, Mieter). Zählen zur Netto-Belegung.")
        hoch = knopf("Excel hochladen", "primary", "hochladen")
        hoch.clicked.connect(lambda: self._import("mieten"))
        karte.aktion(hoch)
        inhalt = QWidget()
        inhalt_lay = QGridLayout(inhalt)
        inhalt_lay.setContentsMargins(0, 0, 0, 0)
        karte.inhalt.addWidget(inhalt)
        self.import_karten["mieten"] = (karte, inhalt_lay)

        self.uwt_karte = Karte("UWT-Blöcke", "Blockbeschulungsplan der BBS (PDF, ganzes Schuljahr), Anreisekalender (Excel) "
                                             "oder An-/Abreiseliste eines Blocks (PDF) – dazu die Klassenübersicht (Excel, Namen und "
                                             "DZ-Partner). Oder einfach in den Ordner „UWT“ legen. Die UWT steht nicht in der "
                                             "Pivot und zählt über den ganzen Block zur Belegung Goslar.")
        uwt_hoch = knopf("Plan / Liste hochladen", "primary", "hochladen")
        uwt_hoch.clicked.connect(self._uwt)
        self.uwt_karte.aktion(uwt_hoch)
        self.uwt_inhalt = QVBoxLayout()
        self.uwt_karte.inhalt.addLayout(self.uwt_inhalt)
        self.mieten_karte = karte

        # Manuelle Einträge
        self.man_karte = Karte("Manuelle Einträge", "Einzelne Belegungen ohne Liste, z. B. DRK, Landkreis, FRAI, Jugendhilfe")
        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)
        self.m_kat = QComboBox()
        self.m_kat.addItems(MANUELLE_KATEGORIEN)
        self.m_ort = QComboBox()
        for s in STANDORTE:
            self.m_ort.addItem(STANDORT_LABEL[s], s)
        heute = date.today()
        self.m_von = DatumFeld(heute)
        self.m_bis = DatumFeld(date(heute.year + 1, heute.month, min(heute.day, 28)))
        self.m_anzahl = QSpinBox()
        self.m_anzahl.setRange(1, 999)
        self.m_anzahl.setFixedWidth(70)
        self.m_text = QLineEdit()
        self.m_text.setPlaceholderText("Bezeichnung (optional)")
        plus = knopf("Hinzufügen", "primary", "plus")
        plus.clicked.connect(self._man_hinzufuegen)
        for c, w in enumerate((self.m_kat, self.m_ort, self.m_von, label("bis", "muted"), self.m_bis)):
            form.addWidget(w, 0, c)
        form.addWidget(label("Anzahl", "muted"), 1, 0)
        form.addWidget(self.m_anzahl, 1, 1)
        form.addWidget(self.m_text, 1, 2, 1, 3)
        form.addWidget(plus, 1, 5)
        form.setColumnStretch(6, 1)
        self.man_karte.inhalt.addLayout(form)
        self.man_tabelle = Tabelle(["Kategorie", "Standort", "Von", "Bis", "Anzahl", "Bezeichnung", ""],
                                   ["l", "l", "l", "l", "r", "l", "l"])
        self.man_karte.inhalt.addWidget(self.man_tabelle)

        # Reiter statt einer langen Seite
        self.reiter = Segment(["Anreisen", "UWT", "Mieten", "Manuelle Einträge", "Quelle && Kapazitäten"], 0)
        self.reiter.geaendert.connect(self._reiter)
        self.lay.addWidget(self.reiter, 0, Qt.AlignLeft)
        self._reiter_seiten = [[self.anr_karte], [self.uwt_karte], [self.mieten_karte], [self.man_karte],
                               [self.quelle_karte, self.kap_karte]]
        for karten in self._reiter_seiten:
            for k in karten:
                self.lay.addWidget(k)
        self.lay.addStretch()
        self._reiter(0)

    def _reiter(self, i: int) -> None:
        for k, karten in enumerate(self._reiter_seiten):
            for karte in karten:
                karte.setVisible(k == i)

    # ---- Anzeige ------------------------------------------------------------------------

    def aktualisieren(self) -> None:
        ds = self.z.ds
        abruf = f"Pivot zuletzt vom Server abgerufen am {ds.pivot.abrufdatum:%d.%m.%Y}" if ds.pivot.abrufdatum else "Abrufdatum unbekannt"
        self.quelle_text.setText(
            f"<b>{ds.quelle}</b><br>{abruf}. Daten vom {ds.erster_tag:%d.%m.%Y} bis {ds.letzter_tag:%d.%m.%Y}; "
            f"Ist-Werte bis {ds.stichtag:%d.%m.%Y}, danach gebuchter Bestand. {len(ds.pivot.haus_standort)} Häuser erkannt.")
        for s, (n, b) in self.kap_felder.items():
            n.setValue(ds.kapazitaet(s))
            b.setValue(ds.kapazitaet(s, True))
        self._import_anzeigen("mieten")
        self._anreisen_anzeigen()
        self._uwt_anzeigen()
        self._man_anzeigen()

    def _import_anzeigen(self, art: str) -> None:
        karte, lay = self.import_karten[art]
        leeren(lay)
        meta = self.z.ds.importe.get(art)
        if not meta:
            leer = Leer("hochladen", f"Noch keine {importe.ARTEN[art]} importiert",
                        "Excel- oder CSV-Datei wählen – Spalten werden automatisch erkannt und können vor dem Import "
                        "geprüft werden.")
            lay.addWidget(leer, 0, 0)
            return
        eintraege = self.z.ds.eintraege_von(quelle=art)
        zeit = datetime.fromisoformat(meta["importiert_am"]).strftime("%d.%m.%Y %H:%M")
        kopf = QHBoxLayout()
        kopf.addWidget(Pille(f"{meta['anzahl']} Einträge", "akzent"))
        kopf.addWidget(label(f"{meta['quelle']} · importiert {zeit}", "klein"))
        kopf.addStretch()
        weg = knopf("Entfernen", "gefahr", "loeschen")
        weg.clicked.connect(lambda: self._import_loeschen(art))
        kopf.addWidget(weg)
        lay.addLayout(kopf, 0, 0)
        tab = Tabelle(["Von", "Bis", "Standort", "Anzahl", "Bezeichnung"], ["l", "l", "l", "r", "l"])
        heute = date.today()
        sortiert = sorted(eintraege, key=lambda e: (e.bis < heute, e.von))
        tab.fuellen([[e.von.strftime("%d.%m.%Y"), "–" if e.nur_termin else ("offen" if e.bis.year >= 2099 else e.bis.strftime("%d.%m.%Y")),
                      STANDORT_LABEL[e.standort], e.anzahl, e.bezeichnung or "–"] for e in sortiert[:200]])
        tab.hoehe_anpassen(8)
        lay.addWidget(tab, 1, 0)
        summen = importe.standorte_in([{"standort": e.standort, "anzahl": e.anzahl} for e in eintraege])
        lay.addWidget(label(" · ".join(f"{STANDORT_LABEL[s]}: {zahl(v)}" for s, v in summen.items()), "klein"), 2, 0)

    def _anreisen_anzeigen(self) -> None:
        personen, listen = anreiseliste.laden()
        heute = date.today()
        filt = self.anr_filter.index()
        if filt == 0:
            auswahl = [p for p in personen if (p.abreise or p.anreise) >= heute - timedelta(days=1)]
        elif filt == 1:
            auswahl = [p for p in personen if p.abreise is None]
        elif filt == 2:
            auswahl = [p for p in personen if p.erinnerung_tage is not None]
        else:
            auswahl = list(personen)
        self._anr_zeilen = auswahl
        zeilen = []
        for p in auswahl:
            stift = knopf("", "icon", "neu", "Abreise und Erinnerung bearbeiten")
            stift.clicked.connect(lambda _=False, p=p: self._person(p))
            if p.erinnerung_tage is None:
                erin = "–"
            elif p.erledigt:
                erin = "erledigt"
            else:
                erin = f"{p.erinnerung_am:%d.%m.} · {erinnerung.KANAL_KURZ.get(p.erinnerung_kanal, '')}"
            zeilen.append([p.anreise.strftime("%d.%m.%Y"), p.name + (" · Tier" if p.tier else "") + (" · …" if p.bemerkung else ""),
                           p.massnahme or p.gruppe,
                           Pille("ja", "ok") if p.internat else Pille("nein", "neutral"),
                           (p.abreise.strftime("%d.%m.%Y") + (" (EMR)" if p.abreise_quelle == "emr" else ""))
                           if p.abreise else Pille("offen", "knapp"), erin, stift])
        self.anr_tabelle.fuellen(zeilen)
        for r, p in enumerate(auswahl):
            if p.bemerkung and self.anr_tabelle.item(r, 1):
                self.anr_tabelle.item(r, 1).setToolTip(p.bemerkung)
            if p.abreise_quelle == "emr" and self.anr_tabelle.item(r, 4):
                self.anr_tabelle.item(r, 4).setToolTip("Automatisch: EMR reisen mittwochs ab – per Stift änderbar")
        self.anr_tabelle.widgets_einpassen()
        self.anr_tabelle.hoehe_anpassen(12)
        self.anr_tabelle.setVisible(bool(zeilen))
        self.anr_leer.setVisible(not personen)
        if personen:
            mit = sum(1 for p in personen if p.internat)
            offen = sum(1 for p in personen if p.internat and p.abreise is None)
            self.anr_info.setText(f"{len(personen)} Personen aus {len(listen)} Listen · {mit} mit Internat · "
                                  f"{offen} davon ohne Abreise" + (f" · {len(auswahl)} angezeigt" if len(auswahl) != len(personen) else ""))
        else:
            self.anr_info.setText("")

    def _uwt_anzeigen(self) -> None:
        leeren(self.uwt_inhalt)
        bloecke = uwt.laden()
        if not bloecke:
            self.uwt_inhalt.addWidget(Leer("hochladen", "Noch keine UWT-Blöcke",
                                           "Anreisekalender (Excel) oder „UWT An- und Abreiseliste“ (PDF) hochladen – "
                                           "Klassen, Anzahl und Zeitraum werden erkannt."))
            return
        heute = date.today().isoformat()
        tab = Tabelle(["Klasse", "Anzahl", "Anreise", "Abreise", ""], ["l", "r", "l", "l", "l"], dehnen=0)
        zeilen = []
        for b in sorted(bloecke, key=lambda b: (b["abreise"] < heute, b["anreise"])):
            weg = knopf("", "icon", "loeschen", "Block entfernen")
            weg.clicked.connect(lambda _=False, b=b: self._uwt_loeschen(b))
            zeilen.append([b["klasse"], b["anzahl"], date.fromisoformat(b["anreise"]).strftime("%d.%m.%Y"),
                           date.fromisoformat(b["abreise"]).strftime("%d.%m.%Y"), weg])
        tab.fuellen(zeilen)
        tab.widgets_einpassen()
        tab.hoehe_anpassen(10)
        self.uwt_inhalt.addWidget(tab)
        aktiv = sum(int(b["anzahl"]) for b in bloecke if b["anreise"] <= heute <= b["abreise"])
        self.uwt_inhalt.addWidget(label(f"{len(bloecke)} Blöcke · heute im Haus: {aktiv}", "klein"))
        klassen, info = uwt.klassen_laden(), uwt.klassen_info()
        if klassen:
            paare = sum(1 for v in klassen.values() for p in v if p.get("dz") not in ("", "allein", None))
            self.uwt_inhalt.addWidget(label(
                f"Klassenübersicht {info.get('datei') or ''}: {len(klassen)} Klassen, "
                f"{sum(len(v) for v in klassen.values())} Teilnehmende, {paare} mit DZ-Partner – "
                "Namen und Doppelzimmer-Paare gelten für alle Blöcke der Klasse.", "klein", umbruch=True))

    def _man_anzeigen(self) -> None:
        roh = laden.manuelle_laden()
        zeilen = []
        for i, e in enumerate(roh):
            weg = knopf("", "icon", "loeschen", "Eintrag löschen")
            weg.clicked.connect(lambda _=False, i=i: self._man_loeschen(i))
            zeilen.append([e.get("typ") or e.get("kategorie"), STANDORT_LABEL.get(e["standort"], e["standort"]),
                           date.fromisoformat(e["von"]).strftime("%d.%m.%Y"), date.fromisoformat(e["bis"]).strftime("%d.%m.%Y"),
                           e["anzahl"], e.get("bezeichnung") or "–", weg])
        self.man_tabelle.fuellen(zeilen)
        self.man_tabelle.widgets_einpassen()
        self.man_tabelle.hoehe_anpassen(10)
        self.man_tabelle.setVisible(bool(zeilen))

    # ---- Aktionen ----------------------------------------------------------------------

    def _kap_speichern(self) -> None:
        werte = {s: {"netto": n.value(), "brutto": max(b.value(), n.value())} for s, (n, b) in self.kap_felder.items()}
        laden.kapazitaeten_speichern(werte)
        self.z.meldung.emit("Kapazitäten gespeichert.", "ok")
        self.z.listen_geaendert.emit()

    def _import(self, art: str) -> None:
        from ..dialoge import ImportDialog

        start = speicher.einstellungen().get(f"import_ordner_{art}") or str(Path.home())
        pfad, _ = QFileDialog.getOpenFileName(self, f"{importe.ARTEN[art]}-Liste wählen", start,
                                              "Tabellen (*.xlsx *.xlsm *.csv);;Alle Dateien (*)")
        if not pfad:
            return
        speicher.einstellung_setzen(f"import_ordner_{art}", str(Path(pfad).parent))
        dialog = ImportDialog(Path(pfad), art, self)
        if dialog.exec():
            self.z.meldung.emit(f"{dialog.anzahl} {importe.ARTEN[art]} importiert.", "ok")
            self.z.listen_geaendert.emit()

    def _datei_start(self, schluessel: str) -> str:
        return speicher.einstellungen().get(schluessel) or str(Path.home())

    def _anreiselisten(self) -> None:
        from ..dialoge import AnreiselistenDialog, erinnerung_abgleichen

        pfade, _ = QFileDialog.getOpenFileNames(self, "Anreiselisten wählen", self._datei_start("import_ordner_anreisen"),
                                                "Anreiselisten oder Einheitsliste (*.xlsx *.xlsm *.csv);;Alle Dateien (*)")
        if not pfade:
            return
        speicher.einstellung_setzen("import_ordner_anreisen", str(Path(pfade[0]).parent))
        dialog = AnreiselistenDialog([Path(p) for p in pfade], self)
        if not dialog.exec():
            return
        b = dialog.bericht
        for p in b.entfernt:
            erinnerung_abgleichen(p, None)
        teile = [f"{b.neu} neu", f"{b.aktualisiert} aktualisiert"] + ([f"{len(b.entfernt)} nicht mehr auf der Liste"] if b.entfernt else [])
        self.z.meldung.emit("Anreisen importiert: " + ", ".join(teile) + ".", "ok")
        self._anreisen_anzeigen()
        self.z.listen_geaendert.emit()
        kuenftig = [t for t in dialog.anreisetage if t >= date.today() - timedelta(days=3)]
        if kuenftig and QMessageBox.question(
                self, "Zimmer zuteilen",
                f"Jetzt Zimmer für die Anreise am {kuenftig[0]:%d.%m.%Y} zuteilen? Das Programm macht einen Vorschlag.") == QMessageBox.Yes:
            self.z.zimmer_anreise = kuenftig[0]
            self.z.navigieren.emit("zimmerplan")

    def _person(self, person) -> None:
        from ..dialoge import PersonDialog, erinnerung_abgleichen

        dialog = PersonDialog(person, self)
        if not dialog.exec():
            return
        neu = dialog.ergebnis
        meldung = erinnerung_abgleichen(person, neu)
        if neu is None:
            anreiseliste.person_loeschen(person.schluessel)
            zp.person_geloescht(person.schluessel)          # sonst blockiert die alte Zuweisung das Zimmer
            self.z.meldung.emit(f"{person.name} entfernt.", "ok")
        else:
            anreiseliste.person_speichern(neu, person.schluessel if person else None)
            zp.person_umbenannt(person.schluessel if person else None, neu.schluessel)
            self.z.meldung.emit(*(meldung or ("Gespeichert.", "ok")))
        self._anreisen_anzeigen()
        self.z.listen_geaendert.emit()

    def _wochen_speichern(self) -> None:
        wert = self.anr_wochen.value()
        if wert != int(speicher.einstellungen().get("anreise_standard_wochen", 0) or 0):
            speicher.einstellung_setzen("anreise_standard_wochen", wert)
            self.z.listen_geaendert.emit()

    def _uwt(self) -> None:
        from ..dialoge import UwtDialog

        pfad, _ = QFileDialog.getOpenFileName(self, "UWT-Kalender oder -Liste wählen", self._datei_start("import_ordner_uwt"),
                                              "UWT-Plan, -Liste oder Klassenübersicht (*.xlsx *.xlsm *.pdf);;Alle Dateien (*)")
        if not pfad:
            return
        speicher.einstellung_setzen("import_ordner_uwt", str(Path(pfad).parent))
        if uwt.ist_klassenliste(Path(pfad)):
            # Klassenübersicht: Teilnehmende und DZ-Partner je Klasse
            klassen, hinweise = uwt.klassen_lesen(Path(pfad))
            if not klassen:
                QMessageBox.warning(self, "Klassenübersicht", "Keine Klassenblätter mit Teilnehmenden gefunden.")
                return
            uwt.klassen_importieren(klassen, Path(pfad).name, hinweise)
            n = sum(len(v) for v in klassen.values())
            text = (f"{len(klassen)} Klassen mit {n} Teilnehmenden übernommen "
                    f"({sum(1 for v in klassen.values() for p in v if p.partner)} mit DZ-Partner).")
            if hinweise:
                QMessageBox.information(self, "Klassenübersicht", text + "\n\n" + "\n".join(hinweise))
            self.z.meldung.emit(text, "ok")
            self._uwt_anzeigen()
            self.z.listen_geaendert.emit()
            return
        dialog = UwtDialog(Path(pfad), self)
        if dialog.exec():
            neu, ersetzt = dialog.ergebnis
            self.z.meldung.emit(f"UWT importiert: {neu} Blöcke neu, {ersetzt} ersetzt.", "ok")
            self._uwt_anzeigen()
            self.z.listen_geaendert.emit()

    def _uwt_loeschen(self, b: dict) -> None:
        if QMessageBox.question(self, "Block entfernen", f"UWT {b['klasse']} ab {date.fromisoformat(b['anreise']):%d.%m.%Y} entfernen?") != QMessageBox.Yes:
            return
        uwt.block_loeschen(b["klasse"], b["anreise"])
        self._uwt_anzeigen()
        self.z.listen_geaendert.emit()

    def _import_loeschen(self, art: str) -> None:
        if QMessageBox.question(self, "Import entfernen", f"Alle importierten {importe.ARTEN[art]} entfernen?") != QMessageBox.Yes:
            return
        importe.datensatz_loeschen(art)
        self.z.listen_geaendert.emit()

    def _man_hinzufuegen(self) -> None:
        von, bis = self.m_von.datum(), self.m_bis.datum()
        if bis < von:
            self.z.meldung.emit("„Bis“ liegt vor „Von“.", "warnung")
            return
        roh = laden.manuelle_laden()
        roh.append({"typ": self.m_kat.currentText(), "standort": self.m_ort.currentData(), "von": von.isoformat(),
                    "bis": bis.isoformat(), "anzahl": self.m_anzahl.value(), "bezeichnung": self.m_text.text().strip()})
        laden.manuelle_speichern(roh)
        self.m_text.clear()
        self.z.meldung.emit("Eintrag gespeichert.", "ok")
        self._man_anzeigen()
        self.z.listen_geaendert.emit()

    def _man_loeschen(self, index: int) -> None:
        roh = laden.manuelle_laden()
        if 0 <= index < len(roh):
            del roh[index]
            laden.manuelle_speichern(roh)
            self._man_anzeigen()
            self.z.listen_geaendert.emit()

    def _profil(self) -> None:
        from ..dialoge import PivotProfilDialog

        if self.z.quelle is None:
            return
        if PivotProfilDialog(self.z.quelle, self).exec():
            self.z.neu_laden.emit(False)
