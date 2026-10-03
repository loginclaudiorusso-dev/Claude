"""Zimmerplan Goslar: Zuteilung je Anreise, Häuser-Übersicht und Zimmer-Stammdaten."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QSpinBox,
    QStackedWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ... import gebaeudeplan, speicher, zimmerexport
from ... import zimmerplan as zp
from .. import theme
from ..basis import Seite, Zustand
from ..widgets import (
    DatumFeld, FlowLayout, Karte, KpiKarte, Leer, Pille, Segment, Tabelle, knopf, label, leeren, zahl,
)

GESCHLECHTER = [("", "?"), ("m", "m"), ("w", "w"), ("d", "d")]
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


class ZimmerplanSeite(Seite):
    titel = "Zimmerplan"
    untertitel = "Internat Goslar – Zimmer zuteilen, Häuser im Blick"
    zeigt_filter = False
    zeigt_bezug = False

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.stand: zp.Planstand | None = None
        self._zuteilungen: list[zp.Zuteilung] = []
        self._fest: dict[str, str] = {}

        # Kopf: Gebäudeplan + Kennzahlen
        kopf = QGridLayout()
        kopf.setSpacing(16)
        self.plan_karte = Karte("Gebäudeplan", "Word-Export aus dem Belegungssystem")
        self.plan_text = label("", "muted", umbruch=True)
        self.plan_karte.inhalt.addWidget(self.plan_text)
        imp = knopf("Gebäudeplan importieren", "primary", "hochladen")
        imp.clicked.connect(self._plan_importieren)
        self.plan_karte.inhalt.addWidget(imp, 0, Qt.AlignLeft)
        kopf.addWidget(self.plan_karte, 0, 0)
        self.kpi = {}
        for i, (k, t) in enumerate((("frei", "Frei heute"), ("belegt", "Belegt heute"), ("gesperrt", "Gesperrt"),
                                    ("offen", "Ohne Zimmer"))):
            karte = KpiKarte(t, sparkline=False)
            self.kpi[k] = karte
            kopf.addWidget(karte, 0, i + 1)
        kopf.setColumnStretch(0, 2)
        for i in range(1, 5):
            kopf.setColumnStretch(i, 1)
        self.lay.addLayout(kopf)

        self.tabs = Segment(["Zuteilen", "Häuser", "Zimmer-Stammdaten"], 0)
        self.tabs.geaendert.connect(self._tab)
        self.lay.addWidget(self.tabs, 0, Qt.AlignLeft)
        self.stapel = QStackedWidget()
        self.lay.addWidget(self.stapel)
        self.stapel.addWidget(self._zuteilen_bauen())
        self.stapel.addWidget(self._haeuser_bauen())
        self.stapel.addWidget(self._stamm_bauen())
        self.lay.addStretch()

    # ------------------------------------------------------------------ Aufbau

    def _zuteilen_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        self.zu_karte = Karte("Zimmer zuteilen", "Vorschlag nach Ihren Regeln – Zimmer, Geschlecht und Tier lassen sich "
                                                 "je Person ändern, danach „Übernehmen“.")
        zeile = QHBoxLayout()
        zeile.setSpacing(8)
        self.anreise = QComboBox()
        self.anreise.setMinimumWidth(360)
        self.anreise.currentIndexChanged.connect(self._anreise_gewaehlt)
        zeile.addWidget(label("Anreise", "klein"))
        zeile.addWidget(self.anreise)
        self.alle = QCheckBox("auch vergangene")
        self.alle.toggled.connect(self._anreisen_fuellen)
        zeile.addWidget(self.alle)
        zeile.addStretch()
        neu = knopf("Neu vorschlagen", "ghost", "funke", "Eigene Änderungen verwerfen und neu berechnen")
        neu.clicked.connect(self._neu_vorschlagen)
        self.b_excel = knopf("Excel-Zimmerliste", "ghost", "tabelle")
        self.b_excel.clicked.connect(self._excel)
        self.b_ok = knopf("Übernehmen", "primary", "haken")
        self.b_ok.clicked.connect(self._uebernehmen)
        for b in (neu, self.b_excel, self.b_ok):
            zeile.addWidget(b)
        self.zu_karte.inhalt.addLayout(zeile)
        self.zu_status = QHBoxLayout()
        self.zu_karte.inhalt.addLayout(self.zu_status)
        self.zu_tabelle = Tabelle(["Name", "Maßnahme", "m/w", "Tier", "Zeitraum", "Zimmer", "Hinweis"],
                                  ["l", "l", "l", "l", "l", "l", "l"], dehnen=6)
        self.zu_tabelle.verticalHeader().setDefaultSectionSize(40)
        self.zu_karte.inhalt.addWidget(self.zu_tabelle)
        self.zu_leer = Leer("personen", "Keine Anreisen", "Anreiselisten unter Daten & Import hochladen – oder "
                                                         "„auch vergangene“ anzeigen.")
        self.zu_karte.inhalt.addWidget(self.zu_leer)
        v.addWidget(self.zu_karte)
        return w

    def _haeuser_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(16)
        leiste = QHBoxLayout()
        leiste.addWidget(label("Stand am", "klein"))
        self.tag = DatumFeld(date.today())
        self.tag.geaendert.connect(lambda _d: self._haeuser_zeigen())
        leiste.addWidget(self.tag)
        self.legende = QHBoxLayout()
        leiste.addSpacing(16)
        leiste.addLayout(self.legende)
        leiste.addStretch()
        export = knopf("Freie Zimmer als Excel", "ghost", "tabelle")
        export.clicked.connect(self._excel_frei)
        leiste.addWidget(export)
        v.addLayout(leiste)
        self.haeuser = QVBoxLayout()
        self.haeuser.setSpacing(16)
        v.addLayout(self.haeuser)
        return w

    def _stamm_bauen(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        karte = Karte("Zimmer-Stammdaten", "Flure, Doppelzimmer, Tier-Zimmer und Bad über den Flur sind aus den "
                                           "Grundrissen abgeleitet – bitte einmal prüfen. Häkchen und Werte per Klick bzw. "
                                           "Doppelklick ändern, dann speichern.")
        leiste = QHBoxLayout()
        self.stamm_haus = Segment(["Haus 2", "Haus 3.1", "Haus 3.2", "Haus 3.3", "Haus 6"], 0)
        self.stamm_haus.geaendert.connect(lambda _i: self._stamm_zeigen())
        leiste.addWidget(self.stamm_haus)
        leiste.addStretch()
        leiste.addWidget(label("Puffer nach Abreise", "klein"))
        self.puffer = QSpinBox()
        self.puffer.setRange(0, 7)
        self.puffer.setSuffix(" Tag(e)")
        self.puffer.setToolTip("0 = am Abreisetag wieder belegbar · 1 = frühestens am Tag nach der Abreise")
        self.puffer.setValue(int(speicher.einstellungen().get("zimmer_puffer", 1)))
        self.puffer.valueChanged.connect(lambda v: (speicher.einstellung_setzen("zimmer_puffer", v), self.neu_laden()))
        leiste.addWidget(self.puffer)
        speichern = knopf("Speichern", "primary", "haken")
        speichern.clicked.connect(self._stamm_speichern)
        leiste.addWidget(speichern)
        karte.inhalt.addLayout(leiste)
        self.stamm = Tabelle(["Zimmer", "Etage", "Flur", "Betten", "Nur Männer", "Tiere", "Gäste", "Im Internat", "Notiz"],
                             ["l", "l", "l", "r", "l", "l", "l", "l", "l"], dehnen=8)
        self.stamm.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.stamm.setFocusPolicy(Qt.StrongFocus)
        karte.inhalt.addWidget(self.stamm)
        v.addWidget(karte)
        return w

    # ------------------------------------------------------------------ Anzeige

    def aktualisieren(self) -> None:
        self.neu_laden()

    def neu_laden(self) -> None:
        self.stand = zp.laden()
        self._kopf_zeigen()
        self._anreisen_fuellen()
        self._tab(self.tabs.index())

    def _tab(self, i: int) -> None:
        self.stapel.setCurrentIndex(i)
        for k in range(self.stapel.count()):
            # nur die sichtbare Seite bestimmt die Höhe
            self.stapel.widget(k).setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred if k == i else QSizePolicy.Ignored)
        self.stapel.adjustSize()
        if i == 1:
            self._haeuser_zeigen()
        elif i == 2:
            self._stamm_zeigen()

    def _kopf_zeigen(self) -> None:
        st = self.stand
        if st.plan is None:
            self.plan_text.setText("Noch kein Gebäudeplan importiert. Ohne Plan sind nur die Gästezimmer bekannt.")
        else:
            stand = f"Stand {st.plan.stand:%d.%m.%Y}" if st.plan.stand else "Stand unbekannt"
            alter = (date.today() - st.plan.stand).days if st.plan.stand else None
            warn = f" · <b>{alter} Tage alt</b> – bitte aktuellen Plan importieren" if alter and alter > 7 else ""
            aktiv = [z for z in st.zimmer if z.aktiv]
            self.plan_text.setText(f"<b>{st.plan.datei}</b> · {stand}{warn}<br>{len(aktiv)} Zimmer mit "
                                   f"{sum(z.betten for z in aktiv)} Betten in Haus 2, 3.1, 3.2, 3.3 und 6 "
                                   f"(inkl. {sum(1 for z in aktiv if z.gaeste)} Gästezimmer)."
                                   + ("<br>" + "<br>".join(st.plan.hinweise[:2]) if st.plan.hinweise else ""))
        heute = date.today()
        zaehler = {"frei": 0, "belegt": 0, "gesperrt": 0}
        for z in st.zimmer:
            if not z.aktiv:
                continue
            status, _ = st.lage.status_am(z.id, heute)
            if status == "teilweise":
                zaehler["frei"] += 1
                zaehler["belegt"] += 1
            elif status == "geplant":
                zaehler["belegt"] += 1
            else:
                zaehler[status] = zaehler.get(status, 0) + 1
        offen = sum(1 for b in st.bedarf if b.von >= heute and not st.zugewiesen(b.schluessel))
        for k, wert, einheit in (("frei", zaehler["frei"], "Zimmer"), ("belegt", zaehler["belegt"], "Zimmer"),
                                 ("gesperrt", zaehler["gesperrt"], "Zimmer"), ("offen", offen, "Anreisen")):
            self.kpi[k].wert.setText(zahl(wert))
            self.kpi[k].einheit.setText(einheit)
            self.kpi[k].pille.setVisible(False)
            self.kpi[k].balken.setVisible(False)
            self.kpi[k].delta.setText("")
            self.kpi[k].detail.setText("")
        self.kpi["offen"].detail.setText("künftige Personen ohne Zimmer")

    # ---- Zuteilen ----------------------------------------------------------------------

    def _anreisen_fuellen(self, *_):
        if self.stand is None:
            return
        alt = self.anreise.currentData()
        ab = date(2000, 1, 1) if self.alle.isChecked() else date.today() - timedelta(days=3)
        self.anreise.blockSignals(True)
        self.anreise.clear()
        for kennung, tag, titel, bs in self.stand.anreisen(ab):
            fertig = sum(1 for b in bs if self.stand.zugewiesen(b.schluessel))
            stand = "alle zugeteilt" if fertig == len(bs) else (f"{fertig}/{len(bs)} zugeteilt" if fertig else "offen")
            self.anreise.addItem(f"{WOCHENTAGE[tag.weekday()]} {tag:%d.%m.%Y} · {titel} · {len(bs)} Personen · {stand}", kennung)
        self.anreise.blockSignals(False)
        if alt is not None and self.anreise.findData(alt) >= 0:
            self.anreise.setCurrentIndex(self.anreise.findData(alt))
        self._anreise_gewaehlt()

    def _bedarf(self) -> list[zp.Bedarf]:
        kennung = self.anreise.currentData()
        return sorted((b for b in self.stand.bedarf if b.von.isoformat() == kennung),
                      key=lambda b: (b.anreise_kennung, b.name))

    def _anreise_gewaehlt(self, *_):
        bedarf = self._bedarf() if self.stand else []
        # Bereits übernommene Zuweisungen gelten als festgelegt
        self._fest = {b.schluessel: z["zimmer"] for b in bedarf if (z := self.stand.zugewiesen(b.schluessel))}
        self._berechnen()

    def _neu_vorschlagen(self) -> None:
        self._fest = {}
        self._berechnen()

    def _berechnen(self) -> None:
        bedarf = self._bedarf() if self.stand else []
        self.zu_leer.setVisible(not bedarf)
        self.zu_tabelle.setVisible(bool(bedarf))
        for b in (self.b_ok, self.b_excel):
            b.setEnabled(bool(bedarf))
        if not bedarf:
            self._zuteilungen = []
            leeren(self.zu_status)
            return
        self._zuteilungen = zp.vorschlagen(self.stand.lage, bedarf, self._fest)
        self._tabelle_fuellen()

    def _tabelle_fuellen(self) -> None:
        t = theme.T
        zeilen, farben = [], {}
        for r, zt in enumerate(self._zuteilungen):
            b = zt.bedarf
            g = QComboBox()
            for wert, text in GESCHLECHTER:
                g.addItem(text + ("*" if wert and wert == b.geschlecht and b.geschlecht_geschaetzt else ""), wert)
            g.setCurrentIndex(max(0, g.findData(b.geschlecht)))
            g.setMinimumWidth(70)
            if b.geschlecht_geschaetzt and b.geschlecht:
                g.setToolTip("* aus dem Vornamen geschätzt – bitte prüfen")
            g.currentIndexChanged.connect(lambda _i, b=b, g=g: self._angabe(b, geschlecht=g.currentData()))
            tier = QCheckBox()
            tier.setChecked(b.tier)
            tier.toggled.connect(lambda an, b=b: self._angabe(b, tier=an))
            zim = QComboBox()
            zim.addItem("— nicht zugeteilt —", None)
            for z in zt.alternativen:
                frei = "" if z.betten == 1 else " · Doppel"
                zim.addItem(f"{z.kurz} · {zp.etage_text(z.etage)} · {z.flur}{frei}", z.id)
            if zt.zimmer:
                zim.setCurrentIndex(max(0, zim.findData(zt.zimmer.id)))
            zim.currentIndexChanged.connect(lambda _i, b=b, zim=zim: self._zimmer(b, zim.currentData()))
            zim.setMinimumWidth(230)
            hinweis = "; ".join(([zt.grund] if zt.zimmer is None else []) + zt.warnungen) or zt.grund
            zeit = f"{b.von:%d.%m.} – {'≈ ' if b.bis_angenommen else ''}{b.bis:%d.%m.%Y}"
            zeilen.append([b.name, b.massnahme, self._zelle(g), self._zelle(tier, 18),
                           zeit, self._zelle(zim), hinweis])
            if zt.zimmer is None:
                farben[(r, 6)] = t.ueber
            elif zt.warnungen:
                farben[(r, 6)] = t.knapp
        self.zu_tabelle.fuellen(zeilen, farben)
        for r in range(len(zeilen)):
            item = self.zu_tabelle.item(r, 6)
            if item and item.text():
                item.setToolTip(item.text())
        self.zu_tabelle.hoehe_anpassen(16)
        self._status_zeigen()

    @staticmethod
    def _zelle(w: QWidget, links: int = 4) -> QWidget:
        h = QWidget()
        lay = QHBoxLayout(h)
        lay.setContentsMargins(links, 2, 4, 2)
        lay.addWidget(w)
        lay.addStretch()
        return h

    def _status_zeigen(self) -> None:
        leeren(self.zu_status)
        zts = self._zuteilungen
        ok = [z for z in zts if z.zimmer]
        self.zu_status.addWidget(Pille(f"{len(ok)} von {len(zts)} untergebracht", "ok" if len(ok) == len(zts) else "knapp"))
        angenommen = sum(1 for z in zts if z.bedarf.bis_angenommen)
        if angenommen:
            p = Pille(f"≈ {angenommen}× Abreise angenommen", "neutral")
            p.setToolTip("Ohne eingetragene Abreise wird eine übliche Dauer je Gruppe angenommen (EMR/Assessment 4 Wochen, "
                         "RVL/RVT 13 Wochen, sonst 52). Abreise unter Daten & Import eintragen.")
            self.zu_status.addWidget(p)
        flure: dict[str, int] = {}
        for z in ok:
            flure[zp.flur_text(z.zimmer)] = flure.get(zp.flur_text(z.zimmer), 0) + 1
        if flure:
            self.zu_status.addWidget(label(" · ".join(f"{f}: {n}" for f, n in sorted(flure.items(), key=lambda x: -x[1])), "klein"))
        warn = sum(1 for z in zts if z.warnungen)
        if warn:
            self.zu_status.addWidget(Pille(f"{warn} Hinweise prüfen", "knapp"))
        gespeichert = sum(1 for z in zts if self.stand.zugewiesen(z.bedarf.schluessel))
        if gespeichert:
            self.zu_status.addWidget(Pille(f"{gespeichert} übernommen", "akzent"))
        self.zu_status.addStretch()

    def _angabe(self, b: zp.Bedarf, **werte) -> None:
        zp.angabe_setzen(b.schluessel, **werte)
        for k, v in werte.items():
            setattr(b, k, v)
        if "geschlecht" in werte:
            b.geschlecht_geschaetzt = False
        self._berechnen()

    def _zimmer(self, b: zp.Bedarf, zid: str | None) -> None:
        if zid:
            self._fest[b.schluessel] = zid
        else:
            self._fest.pop(b.schluessel, None)
        self._berechnen()

    def _uebernehmen(self) -> None:
        n = zp.zuweisungen_speichern(self._zuteilungen)
        ohne = [z.bedarf.schluessel for z in self._zuteilungen if z.zimmer is None]
        zp.zuweisungen_entfernen(set(ohne))
        self.z.meldung.emit(f"{n} Zuweisungen übernommen" + (f", {len(ohne)} ohne Zimmer." if ohne else "."), "ok" if not ohne else "warnung")
        self.neu_laden()

    def _speicherort(self, vorschlag: str) -> Path | None:
        start = speicher.einstellungen().get("export_ordner") or str(Path.home())
        pfad, _ = QFileDialog.getSaveFileName(self, "Excel speichern", str(Path(start) / vorschlag), "Excel (*.xlsx)")
        if not pfad:
            return None
        speicher.einstellung_setzen("export_ordner", str(Path(pfad).parent))
        return Path(pfad if pfad.lower().endswith(".xlsx") else pfad + ".xlsx")

    def _excel(self) -> None:
        if not self._zuteilungen:
            return
        b0 = self._zuteilungen[0].bedarf
        gruppen = self.anreise.currentText().split(" · ")[1] if " · " in self.anreise.currentText() else ""
        titel = f"Zimmerliste Anreise {b0.von:%d.%m.%Y}" + (f" – {gruppen}" if gruppen else "")
        pfad = self._speicherort(f"Zimmerliste_{b0.von:%Y-%m-%d}.xlsx")
        if pfad:
            self._excel_schreiben(pfad, titel, self._zuteilungen, b0.von)

    def _excel_frei(self) -> None:
        tag = self.tag.datum()
        pfad = self._speicherort(f"Freie_Zimmer_{tag:%Y-%m-%d}.xlsx")
        if pfad:
            self._excel_schreiben(pfad, f"Belegung am {tag:%d.%m.%Y}", [], tag)

    def _excel_schreiben(self, pfad: Path, titel: str, zuteilungen, tag: date) -> None:
        try:
            zimmerexport.exportieren(pfad, titel, zuteilungen, self.stand.lage, tag)
        except PermissionError:
            self.z.meldung.emit("Datei ist noch geöffnet – bitte in Excel schließen und erneut versuchen.", "fehler")
            return
        self.z.meldung.emit(f"Gespeichert: {pfad.name}", "ok")
        import os
        import sys

        if sys.platform == "win32":
            os.startfile(str(pfad))

    # ---- Häuser ------------------------------------------------------------------------

    def _haeuser_zeigen(self) -> None:
        t = theme.T
        leeren(self.legende)
        farben = {"frei": (theme.alpha(t.ok, .20), t.text), "teilweise": (theme.alpha(t.knapp, .22), t.text),
                  "belegt": (t.surface_2, t.text_2), "geplant": (t.accent_soft, t.accent),
                  "gesperrt": (theme.alpha(t.ueber, .14), t.text_3)}
        for name, (bg, fg) in farben.items():
            p = QLabel(f"  {name}  ")
            p.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:6px; padding:3px 6px; font-size:11.5px;")
            self.legende.addWidget(p)
        self.legende.addWidget(label("· D = Doppel · T = Tiere · M = nur Männer · G = Gäste", "klein"))
        leeren(self.haeuser)
        st, tag = self.stand, self.tag.datum()
        haeuser: dict[str, list[zp.Zimmer]] = {}
        for z in st.zimmer:
            if z.aktiv:
                haeuser.setdefault(z.haus, []).append(z)
        if not haeuser:
            self.haeuser.addWidget(Leer("haus", "Kein Gebäudeplan", "Gebäudeplan (.docx) importieren."))
            return
        for haus, zimmer in haeuser.items():
            frei = sum(1 for z in zimmer if st.lage.status_am(z.id, tag)[0] in ("frei", "teilweise"))
            karte = Karte(f"Haus {haus}", f"{len(zimmer)} Zimmer · {frei} frei am {tag:%d.%m.%Y}")
            gitter = QGridLayout()
            gitter.setHorizontalSpacing(18)
            gitter.setVerticalSpacing(10)
            etagen = sorted({z.etage for z in zimmer}, key=zp._etage_sort, reverse=True)
            flure = sorted({z.flur for z in zimmer})
            for c, f in enumerate(flure):
                gitter.addWidget(label(f or "–", "klein"), 0, c + 1)
            for r, e in enumerate(etagen, start=1):
                gitter.addWidget(label(zp.etage_text(e), "fett"), r, 0, Qt.AlignTop)
                for c, f in enumerate(flure):
                    feld = QWidget()
                    fl = FlowLayout(feld, abstand=4)
                    for z in sorted((z for z in zimmer if z.etage == e and z.flur == f), key=lambda z: z.nummer):
                        status, bel = st.lage.status_am(z.id, tag)
                        bg, fg = farben[status]
                        merk = "".join(k for k, an in (("D", z.betten > 1), ("T", z.tiere), ("M", z.nur_maenner), ("G", z.gaeste)) if an)
                        kachel = QLabel(f"{z.nr}<span style='font-size:9px'> {merk}</span>" if merk else z.nr)
                        kachel.setStyleSheet(f"background:{bg}; color:{fg}; border-radius:6px; padding:4px 6px; font-size:11.5px;")
                        kachel.setToolTip(self._tooltip(z, status, bel, tag))
                        fl.addWidget(kachel)
                    gitter.addWidget(feld, r, c + 1)
            for c in range(len(flure)):
                gitter.setColumnStretch(c + 1, 1)
            karte.inhalt.addLayout(gitter)
            self.haeuser.addWidget(karte)

    def _tooltip(self, z: zp.Zimmer, status: str, bel, tag: date) -> str:
        zeilen = [f"<b>{z.id}</b> · {zp.flur_text(z)} · {z.betten} Bett{'en' if z.betten > 1 else ''}"]
        for b in bel:
            if b.art == "gesperrt":
                zeilen.append(f"Gesperrt bis {b.bis:%d.%m.%Y} ({b.grund})")
            else:
                zeilen.append(f"{b.name} ({b.massnahme or '–'}) bis {b.bis:%d.%m.%Y}" + (" · geplant" if b.art == "geplant" else ""))
        if status in ("frei", "teilweise"):
            bis = self.stand.lage.frei_bis(z.id, tag)
            zeilen.append(f"frei bis {bis:%d.%m.%Y}" if bis else "frei ohne Folgebelegung")
        if z.notiz:
            zeilen.append(z.notiz)
        return "<br>".join(zeilen)

    # ---- Stammdaten --------------------------------------------------------------------

    def _stamm_zeigen(self) -> None:
        haus = ["2", "3.1", "3.2", "3.3", "6"][self.stamm_haus.index()]
        self._stamm_zimmer = [z for z in self.stand.zimmer if z.haus == haus]
        tab = self.stamm
        tab.blockSignals(True)
        tab.setRowCount(len(self._stamm_zimmer))
        for r, z in enumerate(self._stamm_zimmer):
            werte = [z.id, zp.etage_text(z.etage), z.flur, str(z.betten)]
            for c, v in enumerate(werte):
                item = QTableWidgetItem(v)
                if c in (0, 1):
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 3:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tab.setItem(r, c, item)
            for c, an in ((4, z.nur_maenner), (5, z.tiere), (6, z.gaeste), (7, z.aktiv)):
                item = QTableWidgetItem("")
                item.setFlags((item.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsEditable)
                item.setCheckState(Qt.Checked if an else Qt.Unchecked)
                tab.setItem(r, c, item)
            tab.setItem(r, 8, QTableWidgetItem(z.notiz))
        tab.blockSignals(False)
        tab.hoehe_anpassen(26)

    def _stamm_speichern(self) -> None:
        tab = self.stamm
        alle = {z.id: z for z in self.stand.zimmer}
        for r, z in enumerate(self._stamm_zimmer):
            ziel = alle[z.id]
            ziel.flur = tab.item(r, 2).text().strip()
            try:
                ziel.betten = max(1, int(tab.item(r, 3).text()))
            except ValueError:
                pass
            ziel.nur_maenner = tab.item(r, 4).checkState() == Qt.Checked
            ziel.tiere = tab.item(r, 5).checkState() == Qt.Checked
            ziel.gaeste = tab.item(r, 6).checkState() == Qt.Checked
            ziel.aktiv = tab.item(r, 7).checkState() == Qt.Checked
            ziel.notiz = tab.item(r, 8).text().strip() if tab.item(r, 8) else ""
        zp.stammdaten_speichern(list(alle.values()), self.stand.plan)
        self.z.meldung.emit("Zimmer-Stammdaten gespeichert.", "ok")
        self.neu_laden()

    # ---- Import ------------------------------------------------------------------------

    def _plan_importieren(self) -> None:
        start = speicher.einstellungen().get("import_ordner_gebaeudeplan") or str(Path.home())
        pfad, _ = QFileDialog.getOpenFileName(self, "Gebäudeplan wählen", start, "Word (*.docx);;Alle Dateien (*)")
        if not pfad:
            return
        speicher.einstellung_setzen("import_ordner_gebaeudeplan", str(Path(pfad).parent))
        try:
            plan = gebaeudeplan.lesen(Path(pfad))
        except Exception as exc:
            self.z.meldung.emit(f"Gebäudeplan konnte nicht gelesen werden: {exc}", "fehler")
            return
        gebaeudeplan.speichern(plan)
        belegt = sum(1 for b in plan.belegungen if b.art == "belegt")
        self.z.meldung.emit(f"Gebäudeplan importiert: {len(plan.zimmer)} Zimmer, {belegt} Belegungen.", "ok")
        self.neu_laden()

