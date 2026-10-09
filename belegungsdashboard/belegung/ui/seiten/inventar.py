"""Inventar: Gegenstände anlegen und auf die Zimmer verteilen – mit Übersicht, Excel und Inventarliste."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QMessageBox,
    QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from ... import gebaeudeplan, inventar, speicher
from ... import zimmerplan as zp
from .. import drucken, theme
from ..basis import Seite, Zustand
from ..widgets import FlowLayout, Karte, Pille, Segment, Tabelle, knopf, label, leeren

HAEUSER = ["2", "3.1", "3.2", "3.3", "6"]


class InventarSeite(Seite):
    titel = "Inventar"
    untertitel = "Was steht in welchem Zimmer"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.inv = inventar.Inventar()
        self.zimmer: list[zp.Zimmer] = []
        self._liste: list[zp.Zimmer] = []          # gerade angezeigte Zimmer
        self.tabs = Segment(["Zimmer", "Gegenstände", "Übersicht"], 0)
        self.tabs.geaendert.connect(self._tab)
        self.lay.addWidget(self.tabs, 0, Qt.AlignLeft)
        self.seiten = [self._zimmer_bauen(), self._gegenstaende_bauen(), self._uebersicht_bauen()]
        for w in self.seiten:
            self.lay.addWidget(w)
        self.lay.addStretch()
        # Karten dürfen mit umbrechenden Zeilen wachsen (sonst überlappt im schmalen Fenster der Inhalt)
        for k in self.findChildren(Karte):
            k.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self._tab(0)

    # ---- läuft auch ohne geladene Pivot -------------------------------------------------

    def anstossen(self) -> None:
        self._veraltet = True
        if self.isVisible():
            self._ausfuehren()

    def showEvent(self, e):
        QWidget.showEvent(self, e)
        if self._veraltet:
            self._ausfuehren()

    def aktualisieren(self) -> None:
        plan, _meta = gebaeudeplan.laden()
        self.zimmer = [z for z in zp.stammdaten(plan) if z.aktiv]
        self.inv = inventar.laden()
        self._zimmer_zeigen()
        self._gegenstaende_zeigen()
        self._uebersicht_zeigen()

    def _speichern(self) -> None:
        inventar.speichern(self.inv)

    def _tab(self, i: int) -> None:
        for k, w in enumerate(self.seiten):
            w.setVisible(k == i)

    # ================================================================== Zimmer

    def _zimmer_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        k = Karte("Zimmer", "Ein oder mehrere Zimmer wählen (Strg/Umschalt + Klick) – unten die Ausstattung bearbeiten")
        filt = QWidget()
        f = FlowLayout(filt, abstand=10)
        self.haus = Segment([f"Haus {h}" for h in HAEUSER] + ["Alle"], 0)
        self.haus.geaendert.connect(lambda _i: self._zimmer_zeigen())
        f.addWidget(self.haus)
        self.suche = QLineEdit()
        self.suche.setPlaceholderText("Zimmer oder Gegenstand suchen …")
        self.suche.setClearButtonEnabled(True)
        self.suche.setMinimumWidth(220)
        self.suche.textChanged.connect(lambda _t: self._zimmer_zeigen())
        f.addWidget(self.suche)
        self.ohne = QCheckBox("nur ohne Ausstattung")
        self.ohne.toggled.connect(lambda _a: self._zimmer_zeigen())
        f.addWidget(self.ohne)
        k.inhalt.addWidget(filt)
        self.z_tab = Tabelle(["Zimmer", "Etage", "Betten", "Ausstattung"], ["l", "l", "r", "l"], dehnen=3)
        self.z_tab.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.z_tab.setFocusPolicy(Qt.StrongFocus)
        self.z_tab.setTextElideMode(Qt.ElideRight)
        self.z_tab.itemSelectionChanged.connect(self._auswahl_zeigen)
        k.inhalt.addWidget(self.z_tab)
        zeile = QHBoxLayout()
        self.z_info = label("", "klein")
        zeile.addWidget(self.z_info, 1)
        alle = knopf("Alle angezeigten wählen", "ghost")
        alle.clicked.connect(self.z_tab.selectAll)
        zeile.addWidget(alle)
        k.inhalt.addLayout(zeile)
        v.addWidget(k)

        self.a_karte = Karte("Ausstattung", "")
        self.a_tab = Tabelle(["Gegenstand", "Kategorie", "Anzahl", ""], ["l", "l", "r", "l"], dehnen=0)
        self.a_tab.setSelectionMode(QAbstractItemView.NoSelection)
        self.a_leer = label("", "muted", umbruch=True)
        self.a_karte.inhalt.addWidget(self.a_leer)
        self.a_karte.inhalt.addWidget(self.a_tab)
        # hinzufügen
        add = QWidget()
        fa = FlowLayout(add, abstand=8)
        self.a_gegenstand = QComboBox()
        self.a_gegenstand.setMinimumWidth(220)
        fa.addWidget(self.a_gegenstand)
        self.a_anzahl = QSpinBox()
        self.a_anzahl.setRange(1, 99)
        self.a_anzahl.setPrefix("Anzahl ")
        fa.addWidget(self.a_anzahl)
        self.a_je_bett = QCheckBox("je Bett")
        self.a_je_bett.setToolTip("Anzahl mit der Bettenzahl malnehmen – Doppelzimmer bekommen doppelt so viele")
        fa.addWidget(self.a_je_bett)
        self.a_add = knopf("Hinzufügen", "primary", "plus")
        self.a_add.clicked.connect(self._hinzufuegen)
        fa.addWidget(self.a_add)
        neu = knopf("Neuer Gegenstand", "ghost", "plus")
        neu.clicked.connect(lambda: self._gegenstand_dialog(None, fuer_auswahl=True))
        fa.addWidget(neu)
        self.a_karte.inhalt.addWidget(add)
        # kopieren
        kop = QWidget()
        fk = FlowLayout(kop, abstand=8)
        fk.addWidget(label("Ausstattung übernehmen von Zimmer", "klein"))
        self.a_vorlage = QComboBox()
        self.a_vorlage.setEditable(True)
        self.a_vorlage.setInsertPolicy(QComboBox.NoInsert)
        self.a_vorlage.setMinimumWidth(150)
        self.a_vorlage.lineEdit().setPlaceholderText("z. B. 3.2-204")
        fk.addWidget(self.a_vorlage)
        self.a_kopieren = knopf("Übernehmen", "ghost", "kopieren",
                                "Die gewählten Zimmer bekommen genau die Ausstattung dieses Zimmers (bisherige wird ersetzt)")
        self.a_kopieren.clicked.connect(self._kopieren)
        fk.addWidget(self.a_kopieren)
        self.a_karte.inhalt.addWidget(kop)
        v.addWidget(self.a_karte)
        v.addStretch()
        return w

    def _gewaehlt(self) -> list[zp.Zimmer]:
        sel = self.z_tab.selectionModel()
        reihen = sorted({i.row() for i in sel.selectedRows()}) if sel else []
        return [self._liste[r] for r in reihen if r < len(self._liste)]

    def _zimmer_zeigen(self) -> None:
        if not self.zimmer:
            return
        vorher = {z.id for z in self._gewaehlt()}
        i = self.haus.index()
        text = self.suche.text().strip().lower()
        liste = [z for z in self.zimmer if i >= len(HAEUSER) or z.haus == HAEUSER[i]]
        if text:
            liste = [z for z in liste if text in z.kurz.lower() or text in self.inv.kurztext(z.id).lower()
                     or text in z.nr.lower()]
        if self.ohne.isChecked():
            liste = [z for z in liste if not self.inv.zimmer.get(z.id)]
        self._liste = sorted(liste, key=lambda z: (zp._haus_sort(z.haus), z.nummer))
        self.z_tab.blockSignals(True)
        self.z_tab.fuellen([[z.kurz, zp.etage_text(z.etage), z.betten, self.inv.kurztext(z.id) or "–"]
                            for z in self._liste])
        for r, z in enumerate(self._liste):
            if self.z_tab.item(r, 3):
                self.z_tab.item(r, 3).setToolTip(self.inv.kurztext(z.id))
            if z.id in vorher:          # Auswahl nach dem Neuzeichnen behalten
                self.z_tab.selectionModel().select(self.z_tab.model().index(r, 0),
                                                   QItemSelectionModel.Select | QItemSelectionModel.Rows)
        self.z_tab.blockSignals(False)
        self.z_tab.hoehe_anpassen(12)
        mit = sum(1 for z in self._liste if self.inv.zimmer.get(z.id))
        self.z_info.setText(f"{len(self._liste)} Zimmer, davon {mit} mit Ausstattung")
        vorlagen = sorted((z for z in self.zimmer if self.inv.zimmer.get(z.id)), key=lambda z: (zp._haus_sort(z.haus), z.nummer))
        aktuell = self.a_vorlage.currentText()
        self.a_vorlage.blockSignals(True)
        self.a_vorlage.clear()
        for z in vorlagen:
            self.a_vorlage.addItem(z.kurz, z.id)
        self.a_vorlage.setEditText(aktuell)
        self.a_vorlage.blockSignals(False)
        self._auswahl_zeigen()

    def _auswahl_zeigen(self) -> None:
        gew = self._gewaehlt()
        self.a_gegenstand.clear()
        for g in self.inv.gegenstaende:
            self.a_gegenstand.addItem(f"{g.name}  ·  {g.kategorie}", g.id)
        for w in (self.a_add, self.a_kopieren, self.a_gegenstand, self.a_anzahl, self.a_je_bett):
            w.setEnabled(bool(gew) and (w is self.a_kopieren or bool(self.inv.gegenstaende)))
        if not gew:
            self.a_tab.setVisible(False)
            self.a_leer.setText("Oben ein oder mehrere Zimmer wählen." if self.inv.gegenstaende else
                                "Noch keine Gegenstände – zuerst unter „Gegenstände“ oder mit „Neuer Gegenstand“ anlegen "
                                "(z. B. Bett, Schrank, Schreibtisch, Stuhl, Lampe, Bettdecke).")
            self.a_leer.setVisible(True)
            return
        einzeln = len(gew) == 1
        titel = f"Zimmer {gew[0].kurz}" if einzeln else f"{len(gew)} Zimmer gewählt"
        self.a_leer.setText(f"<b>{titel}</b>" + ("" if einzeln else " – Anzahl = zusammen in allen gewählten Zimmern; "
                                                  "„Hinzufügen“ und „Entfernen“ gelten für alle gewählten."))
        ids = [z.id for z in gew]
        gegenstaende = [g for g in self.inv.gegenstaende if any(self.inv.anzahl(zid, g.id) for zid in ids)]
        zeilen = []
        for g in gegenstaende:
            if einzeln:
                sp = QSpinBox()
                sp.setRange(0, 99)
                sp.setValue(self.inv.anzahl(ids[0], g.id))
                sp.setToolTip("0 = entfernen")
                sp.valueChanged.connect(lambda n, g=g, zid=ids[0]: self._anzahl(zid, g.id, n))
                anzahl = self._zelle(sp)
            else:
                n = [self.inv.anzahl(zid, g.id) for zid in ids]
                anzahl = f"{sum(n)} (in {sum(1 for x in n if x)} von {len(ids)})"
            weg = knopf("", "icon", "loeschen", "Aus " + ("dem Zimmer" if einzeln else "allen gewählten Zimmern") + " entfernen")
            weg.clicked.connect(lambda _=False, g=g, ids=ids: self._entfernen(ids, g.id))
            zeilen.append([g.name, g.kategorie, anzahl, weg])
        self.a_tab.fuellen(zeilen)
        self.a_tab.widgets_einpassen()
        self.a_tab.hoehe_anpassen(max(len(zeilen), 1))
        self.a_tab.setVisible(bool(zeilen))
        if not zeilen:
            self.a_leer.setText(self.a_leer.text() + "<br>Noch nichts zugeordnet – unten Gegenstand wählen und hinzufügen "
                                "oder die Ausstattung eines anderen Zimmers übernehmen.")
        self.a_leer.setVisible(True)

    @staticmethod
    def _zelle(w: QWidget) -> QWidget:
        h = QWidget()
        lay = QHBoxLayout(h)
        lay.setContentsMargins(4, 0, 4, 0)
        lay.addWidget(w, 0, Qt.AlignVCenter)
        lay.addStretch()
        return h

    def _geaendert(self) -> None:
        self._speichern()
        self._zimmer_zeigen()
        self._gegenstaende_zeigen()
        self._uebersicht_zeigen()

    def _anzahl(self, zid: str, gid: str, n: int) -> None:
        self.inv.setzen(zid, gid, n)
        self._speichern()
        if n == 0:
            self._geaendert()
        else:          # Tabelle nicht neu aufbauen – sonst springt der Fokus aus dem Zahlenfeld
            r = next((i for i, z in enumerate(self._liste) if z.id == zid), None)
            if r is not None and self.z_tab.item(r, 3):
                self.z_tab.item(r, 3).setText(self.inv.kurztext(zid) or "–")
            self._gegenstaende_zeigen()
            self._uebersicht_zeigen()

    def _hinzufuegen(self) -> None:
        gid = self.a_gegenstand.currentData()
        gew = self._gewaehlt()
        if not gid or not gew:
            return
        self.inv.hinzufuegen([(z.id, z.betten) for z in gew], gid, self.a_anzahl.value(), self.a_je_bett.isChecked())
        g = self.inv.gegenstand(gid)
        self.z.meldung.emit(f"{g.name} in {len(gew)} Zimmer{'n' if len(gew) > 1 else ''} hinzugefügt.", "ok")
        self._geaendert()
        frei = self.inv.frei(gid)
        if frei is not None and frei < 0:
            self.z.meldung.emit(f"Achtung: {-frei}× {g.name} mehr verteilt als im Bestand.", "warnung")

    def _entfernen(self, ids: list[str], gid: str) -> None:
        g = self.inv.gegenstand(gid)
        if len(ids) > 1 and QMessageBox.question(self, "Entfernen", f"„{g.name}“ aus {len(ids)} Zimmern entfernen?") != QMessageBox.Yes:
            return
        self.inv.entfernen(ids, gid)
        self._geaendert()

    def _kopieren(self) -> None:
        text = self.a_vorlage.currentText().strip().removeprefix("GS-")
        von = next((z for z in self.zimmer if z.kurz.lower() == text.lower()), None)
        gew = [z for z in self._gewaehlt() if von is None or z.id != von.id]
        if von is None:
            self.z.meldung.emit(f"Zimmer „{text}“ nicht gefunden (Schreibweise wie 3.2-204).", "warnung")
            return
        if not gew:
            return
        if not self.inv.zimmer.get(von.id):
            self.z.meldung.emit(f"{von.kurz} hat noch keine Ausstattung.", "warnung")
            return
        mit = [z for z in gew if self.inv.zimmer.get(z.id)]
        if mit and QMessageBox.question(
                self, "Ausstattung übernehmen", f"{len(mit)} der {len(gew)} gewählten Zimmer haben schon Ausstattung – "
                f"durch die von {von.kurz} ersetzen?") != QMessageBox.Yes:
            return
        self.inv.kopieren(von.id, [z.id for z in gew])
        self.z.meldung.emit(f"Ausstattung von {von.kurz} in {len(gew)} Zimmer übernommen.", "ok")
        self._geaendert()

    # ================================================================== Gegenstände

    def _gegenstaende_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        k = Karte("Gegenstände", "Was zum Inventar gehört – mit Bestand, wenn gezählt wird (Rest = im Lager). "
                                 "Doppelklick bearbeitet.")
        zeile = QHBoxLayout()
        neu = knopf("Neuer Gegenstand", "primary", "plus")
        neu.clicked.connect(lambda: self._gegenstand_dialog(None))
        zeile.addWidget(neu)
        self.g_bearbeiten = knopf("Bearbeiten", "ghost")
        self.g_bearbeiten.clicked.connect(lambda: self._gegenstand_dialog(self._g_gewaehlt()))
        zeile.addWidget(self.g_bearbeiten)
        zeile.addStretch()
        k.inhalt.addLayout(zeile)
        self.g_tab = Tabelle(["Gegenstand", "Kategorie", "Bestand", "in Zimmern", "im Lager", "Notiz"],
                             ["l", "l", "r", "r", "r", "l"], dehnen=5)
        self.g_tab.setTextElideMode(Qt.ElideRight)
        self.g_tab.setFocusPolicy(Qt.StrongFocus)
        self.g_tab.itemSelectionChanged.connect(self._wo_zeigen)
        self.g_tab.doubleClicked.connect(lambda _i: self._gegenstand_dialog(self._g_gewaehlt()))
        k.inhalt.addWidget(self.g_tab)
        self.g_leer = label("Noch keine Gegenstände angelegt.", "muted")
        k.inhalt.addWidget(self.g_leer)
        v.addWidget(k)
        self.wo_karte = Karte("Wo steht das?", "")
        self.wo_text = label("", "", umbruch=True)
        self.wo_karte.inhalt.addWidget(self.wo_text)
        v.addWidget(self.wo_karte)
        v.addStretch()
        return w

    def _g_gewaehlt(self) -> inventar.Gegenstand | None:
        sel = self.g_tab.selectionModel()
        r = sel.selectedRows()[0].row() if sel and sel.selectedRows() else None
        return self.inv.gegenstaende[r] if r is not None and r < len(self.inv.gegenstaende) else None

    def _gegenstaende_zeigen(self) -> None:
        t = theme.T
        vorher = self._g_gewaehlt()
        zeilen, farben = [], {}
        for r, g in enumerate(self.inv.gegenstaende):
            frei = self.inv.frei(g.id)
            zeilen.append([g.name, g.kategorie, "–" if g.bestand is None else g.bestand, self.inv.verteilt(g.id),
                           "–" if frei is None else frei, g.notiz])
            if frei is not None and frei < 0:
                farben[(r, 4)] = t.ueber
        self.g_tab.blockSignals(True)
        self.g_tab.fuellen(zeilen, farben)
        if vorher and vorher in self.inv.gegenstaende:
            self.g_tab.selectRow(self.inv.gegenstaende.index(vorher))
        self.g_tab.blockSignals(False)
        self.g_tab.hoehe_anpassen(16)
        self.g_tab.setVisible(bool(zeilen))
        self.g_leer.setVisible(not zeilen)
        self.g_bearbeiten.setEnabled(bool(zeilen))
        self._wo_zeigen()

    def _wo_zeigen(self) -> None:
        g = self._g_gewaehlt()
        self.wo_karte.setVisible(g is not None)
        if g is None:
            return
        wo = self.inv.wo(g.id)
        if not wo:
            self.wo_text.setText(f"„{g.name}“ steht noch in keinem Zimmer.")
            return
        je_haus: dict[str, list[str]] = {}
        haus_von = {z.id: z.haus for z in self.zimmer}
        for zid, n in wo:
            je_haus.setdefault(haus_von.get(zid, "?"), []).append(zid.removeprefix("GS-") + (f" ({n}×)" if n > 1 else ""))
        self.wo_text.setText(f"<b>{g.name}</b>: {self.inv.verteilt(g.id)} Stück in {len(wo)} Zimmern<br>"
                             + "<br>".join(f"Haus {h}: {', '.join(zs)}" for h, zs in sorted(je_haus.items())))

    def _gegenstand_dialog(self, g: inventar.Gegenstand | None, fuer_auswahl: bool = False) -> None:
        dlg = GegenstandDialog(g, self)
        if not dlg.exec():
            return
        if dlg.loeschen:
            n = self.inv.verteilt(g.id)
            if QMessageBox.question(self, "Gegenstand löschen", f"„{g.name}“ löschen?"
                                    + (f" Er wird auch aus {len(self.inv.wo(g.id))} Zimmern ({n} Stück) entfernt." if n else "")
                                    ) != QMessageBox.Yes:
                return
            self.inv.gegenstand_loeschen(g.id)
            self.z.meldung.emit(f"„{g.name}“ gelöscht.", "ok")
            self._geaendert()
            return
        try:
            self.inv.gegenstand_speichern(dlg.ergebnis)
        except ValueError as exc:
            self.z.meldung.emit(str(exc), "warnung")
            return
        self._geaendert()
        if fuer_auswahl:
            i = self.a_gegenstand.findData(dlg.ergebnis.id)
            self.a_gegenstand.setCurrentIndex(max(i, 0))

    # ================================================================== Übersicht

    def _uebersicht_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        k = Karte("Übersicht je Haus", "Stück je Haus (H2 = Haus 2 …), gesamt in Zimmern, Bestand und was noch im Lager ist")
        self.ue_pillen = QWidget()
        self.ue_flow = FlowLayout(self.ue_pillen, abstand=6)
        k.inhalt.addWidget(self.ue_pillen)
        self.ue_tab = Tabelle(["Gegenstand"] + [f"H{h}" for h in HAEUSER] + ["gesamt", "Bestand", "Lager"],
                              ["l"] + ["r"] * (len(HAEUSER) + 3), dehnen=0)
        self.ue_tab.setTextElideMode(Qt.ElideRight)
        k.inhalt.addWidget(self.ue_tab)
        knoepfe = QWidget()
        fk = FlowLayout(knoepfe, abstand=8)
        ex = knopf("Excel exportieren", "primary", "tabelle", "Zimmer × Gegenstand, Bestand und Liste je Zimmer")
        ex.clicked.connect(self._excel)
        fk.addWidget(ex)
        self.ue_haus = QComboBox()
        self.ue_haus.addItem("Alle Häuser", None)
        for h in HAEUSER:
            self.ue_haus.addItem(f"Haus {h}", h)
        fk.addWidget(self.ue_haus)
        dr = knopf("Inventarliste drucken", "ghost", "datei", "Je Zimmer zum Abhaken beim Rundgang")
        dr.clicked.connect(lambda: self._drucken(False))
        fk.addWidget(dr)
        pdf = knopf("PDF", "ghost", "runter")
        pdf.clicked.connect(lambda: self._drucken(True))
        fk.addWidget(pdf)
        k.inhalt.addWidget(knoepfe)
        v.addWidget(k)
        v.addStretch()
        return w

    def _uebersicht_zeigen(self) -> None:
        t = theme.T
        haus_von = {z.id: z.haus for z in self.zimmer}
        je_haus = self.inv.je_haus(haus_von)
        zeilen, farben = [], {}
        for r, g in enumerate(self.inv.gegenstaende):
            h = je_haus.get(g.id, {})
            frei = self.inv.frei(g.id)
            zeilen.append([g.name] + [h.get(x) or "" for x in HAEUSER]
                          + [self.inv.verteilt(g.id), "–" if g.bestand is None else g.bestand, "–" if frei is None else frei])
            if frei is not None and frei < 0:
                farben[(r, len(HAEUSER) + 3)] = t.ueber
        self.ue_tab.fuellen(zeilen, farben)
        self.ue_tab.hoehe_anpassen(20)
        self.ue_tab.setVisible(bool(zeilen))
        leeren(self.ue_flow)
        ohne = sum(1 for z in self.zimmer if not self.inv.zimmer.get(z.id) and not z.gaeste)
        mit = sum(1 for z in self.zimmer if self.inv.zimmer.get(z.id))
        self.ue_flow.addWidget(Pille(f"{mit} Zimmer ausgestattet", "ok" if mit else "neutral"))
        p = Pille(f"{ohne} Zimmer ohne Ausstattung", "knapp" if ohne else "ok")
        p.setToolTip("ohne Gästezimmer – unter „Zimmer“ mit „nur ohne Ausstattung“ filtern")
        self.ue_flow.addWidget(p)
        zu_viel = [g.name for g in self.inv.gegenstaende if (f := self.inv.frei(g.id)) is not None and f < 0]
        if zu_viel:
            p = Pille(f"mehr verteilt als vorhanden: {', '.join(zu_viel[:3])}" + (" …" if len(zu_viel) > 3 else ""), "ueber")
            self.ue_flow.addWidget(p)

    def _excel(self) -> None:
        start = speicher.einstellungen().get("export_ordner") or str(Path.home())
        pfad, _ = QFileDialog.getSaveFileName(self, "Excel speichern", str(Path(start) / "Inventar_Zimmer.xlsx"), "Excel (*.xlsx)")
        if not pfad:
            return
        speicher.einstellung_setzen("export_ordner", str(Path(pfad).parent))
        pfad = Path(pfad if pfad.lower().endswith(".xlsx") else pfad + ".xlsx")
        try:
            inventar.excel_speichern(pfad, self.inv, self.zimmer)
        except PermissionError:
            self.z.meldung.emit("Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", "fehler")
            return
        self.z.meldung.emit(f"Gespeichert: {pfad.name}", "ok")

    def _drucken(self, pdf: bool) -> None:
        haus = self.ue_haus.currentData()
        if not any(self.inv.zimmer.get(z.id) for z in self.zimmer if haus is None or z.haus == haus):
            self.z.meldung.emit("Noch keine Ausstattung zugeordnet.", "warnung")
            return
        drucken.html_ausgeben(self, self.z, inventar.druck_html(self.inv, self.zimmer, haus), False,
                              f"Inventarliste{'_Haus_' + haus if haus else ''}.pdf" if pdf else None)


class GegenstandDialog(QDialog):
    def __init__(self, g: inventar.Gegenstand | None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gegenstand bearbeiten" if g else "Neuer Gegenstand")
        self.loeschen = False
        self._id = g.id if g else None
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 20, 22, 18)
        v.setSpacing(14)
        f = QFormLayout()
        f.setHorizontalSpacing(14)
        f.setVerticalSpacing(10)
        self.name = QLineEdit(g.name if g else "")
        self.name.setPlaceholderText("z. B. Schreibtischstuhl")
        f.addRow("Name", self.name)
        self.kategorie = QComboBox()
        self.kategorie.setEditable(True)
        self.kategorie.addItems(inventar.KATEGORIEN)
        self.kategorie.setCurrentText(g.kategorie if g else "Möbel")
        f.addRow("Kategorie", self.kategorie)
        bestand = QHBoxLayout()
        self.zaehlen = QCheckBox("Bestand zählen")
        self.zaehlen.setChecked(bool(g and g.bestand is not None))
        self.bestand = QSpinBox()
        self.bestand.setRange(0, 9999)
        self.bestand.setValue(g.bestand if g and g.bestand is not None else 0)
        self.bestand.setEnabled(self.zaehlen.isChecked())
        self.zaehlen.toggled.connect(self.bestand.setEnabled)
        bestand.addWidget(self.zaehlen)
        bestand.addWidget(self.bestand)
        bestand.addStretch()
        f.addRow("Insgesamt", bestand)
        self.notiz = QLineEdit(g.notiz if g else "")
        self.notiz.setPlaceholderText("optional – z. B. Inventarnummern, Lieferant")
        f.addRow("Notiz", self.notiz)
        v.addLayout(f)
        v.addWidget(label("Mit Bestand zeigt das Programm, wie viele noch im Lager sind – und warnt, wenn mehr verteilt "
                          "als vorhanden ist.", "klein", umbruch=True))
        unten = QHBoxLayout()
        if g:
            weg = knopf("Löschen", "ghost", "loeschen")
            weg.clicked.connect(self._loeschen)
            unten.addWidget(weg)
        unten.addStretch()
        ab = knopf("Abbrechen", "ghost")
        ab.clicked.connect(self.reject)
        ok = knopf("Speichern", "primary", "haken")
        ok.clicked.connect(self._ok)
        unten.addWidget(ab)
        unten.addWidget(ok)
        v.addLayout(unten)
        self.resize(520, 300)
        self.name.setFocus()

    def _loeschen(self) -> None:
        self.loeschen = True
        self.accept()

    def _ok(self) -> None:
        if not self.name.text().strip():
            self.name.setFocus()
            return
        g = inventar.Gegenstand(self.name.text().strip(), self.kategorie.currentText().strip() or "Sonstiges",
                                self.bestand.value() if self.zaehlen.isChecked() else None, self.notiz.text().strip())
        if self._id:
            g.id = self._id
        self.ergebnis = g
        self.accept()
