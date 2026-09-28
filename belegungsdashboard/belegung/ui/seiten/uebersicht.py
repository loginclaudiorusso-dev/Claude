"""Übersicht: Lage heute, Verlauf mit Prognose, Zusammensetzung, nächste Monate, Anreisen."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from ...konfig import GESAMT, STANDORT_LABEL, STANDORTE, ampel_stufe
from .. import theme
from ..basis import Seite, Zustand
from ..charts import VerlaufChart
from ..widgets import (
    DEUTSCHE_MONATE, Donut, Hinweis, Karte, KpiKarte, Legende, Leer, Pille, Segment, Tabelle, label, leeren,
    prozent, rolle, zahl,
)


def _geglaettet(df):
    """7-Tage-Mittel für die Übersicht (Wochenend-Zacken ausblenden, Trend zeigen)."""
    df = df.copy()
    for spalte in ("wert", "lo80", "hi80", "gesichert"):
        df[spalte] = df[spalte].rolling(7, center=True, min_periods=1).mean()
    return df


class UebersichtSeite(Seite):
    titel = "Übersicht"
    untertitel = "Lage heute und Ausblick"

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.hinweise = QVBoxLayout()
        self.hinweise.setSpacing(8)
        self.lay.addLayout(self.hinweise)

        kpis = QGridLayout()
        kpis.setSpacing(16)
        self.kpis: dict[str, KpiKarte] = {}
        for i, s in enumerate([GESAMT] + STANDORTE):
            k = KpiKarte(STANDORT_LABEL[s], farbe_punkt=theme.T.standort[s])
            k.setProperty("klickbar", True)
            k.setCursor(Qt.PointingHandCursor)
            k.setToolTip(f"{STANDORT_LABEL[s]} auswählen")
            k.geklickt.connect(lambda s=s: self.z.standort_setzen(s))
            self.kpis[s] = k
            kpis.addWidget(k, 0, i)
            kpis.setColumnStretch(i, 1)
        self.lay.addLayout(kpis)

        self.verlauf_karte = Karte("Verlauf und Prognose", "Ist-Belegung, danach Prognose mit 80 %-Spanne")
        self.fenster = Segment(["6 M", "12 M", "24 M"], 1)
        self.fenster.geaendert.connect(lambda _i: self.anstossen())
        self.verlauf_karte.aktion(self.fenster)
        self.verlauf = VerlaufChart(hoehe=3.3)
        self.verlauf_karte.inhalt.addWidget(self.verlauf)

        self.zus_karte = Karte("Zusammensetzung heute")
        zus = QVBoxLayout()
        self.donut = Donut()
        self.donut.setFixedHeight(210)
        zus.addWidget(self.donut)
        self.legende = Legende()
        zus.addWidget(self.legende)
        zus.addStretch()
        self.zus_karte.inhalt.addLayout(zus)
        self.zus_karte.setMinimumWidth(300)
        self.zeile(self.verlauf_karte, self.zus_karte, stretch=[3, 1])

        self.monate_karte = Karte("Die nächsten Monate", "Ø belegte Plätze inkl. Verträge")
        self.monate = Tabelle(["Monat", "Erwartet", "80 %-Spanne", "Gesichert", "Auslastung"],
                              ["l", "r", "r", "r", "l"], dehnen=4)
        self.monate_karte.inhalt.addWidget(self.monate)
        self.anreisen_karte = Karte("Anstehende Anreisen", "Nächste 21 Tage")
        self.anreisen_inhalt = QVBoxLayout()
        self.anreisen_karte.inhalt.addLayout(self.anreisen_inhalt)
        self.zeile(self.monate_karte, self.anreisen_karte, stretch=[3, 2])
        self.lay.addStretch()

    def theme_aktualisieren(self) -> None:
        for s, k in self.kpis.items():
            k.farbe_punkt(theme.T.standort[s])

    def aktualisieren(self) -> None:
        ds, z, t = self.z.ds, self.z, theme.T
        tag = ds.stichtag
        self._hinweise()

        for s, k in self.kpis.items():
            rolle(k, aktiv=(s == z.standort))
            auf = ds.aufschluesselung(s, tag, z.brutto)
            vor = float(ds.belegung(s, tag - timedelta(days=7), tag - timedelta(days=7), z.brutto).iloc[0])
            k.wert.setText(zahl(auf.belegt))
            k.einheit.setText("belegt")
            d = auf.belegt - vor
            pfeil = "▲" if d > 0 else ("▼" if d < 0 else "▶")
            k.delta.setText(f"{pfeil} {zahl(abs(d))} ggü. Vorwoche")
            if auf.kapazitaet:
                stufe, text = ampel_stufe(auf.anteil)
                k.pille.setzen(stufe, prozent(auf.anteil))
                k.pille.setToolTip(text)
                k.pille.setVisible(True)
                k.detail.setText(f"von {zahl(auf.kapazitaet)} Plätzen · {zahl(auf.frei)} frei")
                k.balken.setzen(auf.anteil, {"ok": t.ok, "knapp": t.knapp, "kritisch": t.kritisch, "ueber": t.ueber}[stufe])
                k.balken.setVisible(True)
            else:
                k.pille.setVisible(False)
                k.balken.setVisible(False)
                k.detail.setText("Kapazität nicht hinterlegt")
            reihe = ds.belegung(s, tag - timedelta(days=89), tag, z.brutto)
            k.spark.setzen(list(reihe.to_numpy()), t.standort[s])

        self._verlauf()
        self._zusammensetzung()
        self._monate()
        self._anreisen()

    def _hinweise(self) -> None:
        leeren(self.hinweise)
        for text in self.z.ds.hinweise:
            art = "warnung" if ("fehlgeschlagen" in text or "Keine Kapazität" in text) else "info"
            aktion = "Kapazitäten eintragen" if "Kapazität" in text else None
            h = Hinweis(text, art, aktion)
            if h.knopf:
                h.knopf.clicked.connect(lambda: self.z.navigieren.emit("daten"))
            self.hinweise.addWidget(h)

    def _verlauf(self) -> None:
        ds, z, t = self.z.ds, self.z, theme.T
        monate = [6, 12, 24][self.fenster.index()]
        von = max(ds.stichtag - timedelta(days=int(monate * 30.4 * 0.6)), ds.erster_tag)
        bis = ds.stichtag + timedelta(days=int(monate * 30.4 * 0.4))
        if z.standort == GESAMT:
            reihen = {STANDORT_LABEL[s]: (_geglaettet(ds.verlauf(s, von, bis, z.brutto)), t.standort[s]) for s in STANDORTE}
            self.verlauf.zeichnen(reihen, None, ds.stichtag)
            self.verlauf_karte.untertitel("Standorte im Vergleich, 7-Tage-Mittel · gestrichelt: Prognose mit 80 %-Spanne")
        else:
            reihen = {STANDORT_LABEL[z.standort]: (_geglaettet(ds.verlauf(z.standort, von, bis, z.brutto)), t.standort[z.standort])}
            self.verlauf.zeichnen(reihen, ds.kapazitaet(z.standort, z.brutto) or None, ds.stichtag, bestand=True)
            self.verlauf_karte.untertitel("7-Tage-Mittel · gestrichelt: Prognose mit 80 %-Spanne · gepunktet: gesicherter Bestand")

    def _zusammensetzung(self) -> None:
        ds, z, t = self.z.ds, self.z, theme.T
        auf = ds.aufschluesselung(z.standort, ds.stichtag, z.brutto)
        teile = [(k, v, t.kategorie.get(k, t.text_3)) for k, v in auf.teile.items()]
        if auf.kapazitaet:
            teile.append(("frei", auf.frei, t.surface_2))
        mitte = prozent(auf.anteil) if auf.kapazitaet else zahl(auf.belegt)
        unten = f"{zahl(auf.belegt)} von {zahl(auf.kapazitaet)}" if auf.kapazitaet else "belegt"
        self.donut.setzen(teile, mitte, unten)
        self.legende.setzen([(f, n, zahl(v)) for n, v, f in teile])
        self.zus_karte.titel_label.setText(f"Zusammensetzung {STANDORT_LABEL[z.standort]}")

    def _monate(self) -> None:
        ds, z = self.z.ds, self.z
        start = date(ds.stichtag.year, ds.stichtag.month, 1)
        zeilen = []
        for i in range(0, 7):
            m = (pd.Timestamp(start) + pd.DateOffset(months=i)).date()
            mp = ds.monatsprognose(z.standort, m, z.brutto)
            if not mp:
                continue
            if mp["kapazitaet"]:
                stufe, _ = ampel_stufe(mp["anteil_hi80"])
                pille = Pille(prozent(mp["anteil"]), stufe)
                pille.setToolTip(f"Im ungünstigen Fall (obere 80 %-Grenze) {prozent(mp['anteil_hi80'])}")
                zelle = QWidget()
                h = QHBoxLayout(zelle)
                h.setContentsMargins(8, 0, 0, 0)
                h.addWidget(pille)
                h.addStretch()
            else:
                zelle = "–"
            name = f"{DEUTSCHE_MONATE[m.month - 1]} {m.year}" + (" (laufend)" if mp["art"] == "laufend" else "")
            zeilen.append([name, zahl(mp["erwartet"]), f"{zahl(mp['lo80'])} – {zahl(mp['hi80'])}",
                           zahl(mp["gesichert"]) if mp["gesichert"] is not None else "–", zelle])
        self.monate.fuellen(zeilen)
        self.monate.hoehe_anpassen()

    def _anreisen(self) -> None:
        ds, z = self.z.ds, self.z
        leeren(self.anreisen_inhalt)
        if "anreisen" not in ds.importe:
            leer = Leer("hochladen", "Noch keine Anreisen", "Excel-Liste mit geplanten Anreisen hochladen – sie fließt "
                        "in Übersicht, Prognose und Assistent ein.", "Anreisen hochladen")
            leer.knopf.clicked.connect(lambda: self.z.navigieren.emit("daten"))
            self.anreisen_inhalt.addWidget(leer)
            return
        liste = ds.anreisen(z.standort, date.today(), date.today() + timedelta(days=20))
        if not liste:
            self.anreisen_inhalt.addWidget(Leer("kalender", "Keine Anreisen", "In den nächsten drei Wochen sind keine Anreisen geplant."))
            return
        summe = sum(e.anzahl for e in liste)
        self.anreisen_inhalt.addWidget(label(f"{zahl(summe)} Personen in {len(liste)} Einträgen", "muted"))
        tab = Tabelle(["Datum", "Standort", "Anzahl", "Bezeichnung"], ["l", "l", "r", "l"])
        tab.fuellen([[e.von.strftime("%d.%m."), STANDORT_LABEL[e.standort], e.anzahl, e.bezeichnung or "–"] for e in liste[:12]])
        tab.hoehe_anpassen(8)
        self.anreisen_inhalt.addWidget(tab)
