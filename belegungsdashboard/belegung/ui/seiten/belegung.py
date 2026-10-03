"""Belegung im Detail: frei wählbarer Zeitraum, Zusammensetzung, Personentage, Häuser, Muster."""

from __future__ import annotations

import pandas as pd
from PySide6.QtWidgets import QGridLayout

from ...konfig import GESAMT, STANDORT_LABEL, STANDORTE
from .. import theme
from ..basis import Seite, Zustand
from ..charts import BalkenChart, HeatmapChart, StapelChart, VerlaufChart
from ..widgets import DEUTSCHE_MONATE, Karte, KpiKarte, Segment, Tabelle, ZeitraumLeiste, prozent, zahl


class BelegungSeite(Seite):
    titel = "Belegung"
    untertitel = "Beliebiger Zeitraum – Ist-Werte, bei Zukunftstagen Prognose"

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        self.zeitraum = ZeitraumLeiste(zustand.ds.stichtag if zustand.ds else pd.Timestamp.today().date(), vorgabe=1)
        self.zeitraum.geaendert.connect(lambda *_: self.anstossen())
        self.lay.addWidget(self.zeitraum)

        kpis = QGridLayout()
        kpis.setSpacing(16)
        self.k_mittel = KpiKarte("Ø Belegung", sparkline=False)
        self.k_max = KpiKarte("Höchstwert", sparkline=False)
        self.k_min = KpiKarte("Tiefstwert", sparkline=False)
        self.k_tage = KpiKarte("Personentage", sparkline=False)
        self.k_ausl = KpiKarte("Ø Auslastung", sparkline=False)
        for i, k in enumerate((self.k_mittel, self.k_max, self.k_min, self.k_tage, self.k_ausl)):
            k.wert.setProperty("rolle", "kpi_wert_klein")
            kpis.addWidget(k, 0, i)
            kpis.setColumnStretch(i, 1)
        self.lay.addLayout(kpis)

        self.verlauf_karte = Karte("Tagesverlauf")
        self.ansicht = Segment(["Zusammensetzung", "Standorte"], 0)
        self.ansicht.geaendert.connect(lambda _i: self.anstossen())
        self.verlauf_karte.aktion(self.ansicht)
        self.stapel = StapelChart(hoehe=3.4)
        self.linien = VerlaufChart(hoehe=3.4)
        self.verlauf_karte.inhalt.addWidget(self.stapel)
        self.verlauf_karte.inhalt.addWidget(self.linien)
        self.lay.addWidget(self.verlauf_karte)

        self.monate_karte = Karte("Personentage je Monat", "Summe der belegten Plätze über alle Tage; hell = Prognose")
        self.balken = BalkenChart(hoehe=2.6)
        self.monate_karte.inhalt.addWidget(self.balken)
        self.lay.addWidget(self.monate_karte)

        self.haus_karte = Karte("Häuser", "Belegung laut Pivot (nur Reha)")
        self.haeuser = Tabelle(["Haus", "Standort", "Am Ende des Zeitraums", "Ø im Zeitraum", "Höchstwert"])
        self.haus_karte.inhalt.addWidget(self.haeuser)
        self.muster_karte = Karte("Wochentags- und Saisonmuster", "Ø Ist-Belegung (Reha) je Monat und Wochentag, letzte 4 Jahre")
        self.heatmap = HeatmapChart()
        self.muster_karte.inhalt.addWidget(self.heatmap)
        self.zeile(self.haus_karte, self.muster_karte, stretch=[2, 3])
        self.lay.addStretch()
        self._letzter_stichtag = None

    def aktualisieren(self) -> None:
        ds, z, t = self.z.ds, self.z, theme.T
        if self._letzter_stichtag != ds.stichtag:
            self._letzter_stichtag = ds.stichtag
            self.zeitraum.blockSignals(True)
            self.zeitraum.ende_setzen(ds.stichtag)
            self.zeitraum.blockSignals(False)
        von, bis = self.zeitraum.zeitraum()
        von = max(von, ds.erster_tag)
        s = z.standort
        df = ds.verlauf(s, von, bis, z.brutto)
        w = df["wert"]
        kap = ds.kapazitaet(s, z.brutto)
        prognose = (~df["ist"]).any()
        self.k_mittel.wert.setText(zahl(float(w.mean())))
        self.k_mittel.detail.setText("inkl. Prognose" if prognose else f"{len(w)} Tage")
        self.k_max.wert.setText(zahl(float(w.max())))
        self.k_max.detail.setText(f"am {w.idxmax():%d.%m.%Y}")
        self.k_min.wert.setText(zahl(float(w.min())))
        self.k_min.detail.setText(f"am {w.idxmin():%d.%m.%Y}")
        self.k_tage.wert.setText(zahl(float(w.sum())))
        self.k_tage.detail.setText(f"Ø {zahl(float(w.mean()))} pro Tag")
        self.k_ausl.wert.setText(prozent(float(w.mean()) / kap) if kap else "–")
        self.k_ausl.detail.setText(f"Spitze {prozent(float(w.max()) / kap)}" if kap else "Kapazität fehlt")

        zusammensetzung = self.ansicht.index() == 0
        self.stapel.setVisible(zusammensetzung)
        self.linien.setVisible(not zusammensetzung)
        if zusammensetzung:
            kat = ds.kategorien(s, von, bis, z.brutto)
            ist = df["ist"].to_numpy()
            if (~ist).any():  # Zukunft: Reha durch Prognose ersetzen
                kat = kat.copy()
                andere = kat.drop(columns=["Reha"] + (["Anreise"] if "Anreise" in kat else [])).sum(axis=1)
                kat.loc[~ist, "Reha"] = (df["wert"] - andere)[~ist]
                if "Anreise" in kat:
                    kat.loc[~ist, "Anreise"] = 0
                    kat = kat.loc[:, (kat != 0).any(axis=0) | (kat.columns == "Reha")]
            self.stapel.zeichnen(kat, kap or None, ds.stichtag)
            self.verlauf_karte.titel_label.setText(f"Tagesverlauf {STANDORT_LABEL[s]} nach Belegungsart")
        else:
            reihen = {STANDORT_LABEL[x]: (ds.verlauf(x, von, bis, z.brutto), t.standort[x]) for x in STANDORTE}
            if s != GESAMT:
                reihen = {STANDORT_LABEL[s]: reihen[STANDORT_LABEL[s]]}
            self.linien.zeichnen(reihen, kap if s != GESAMT else None, ds.stichtag)
            self.verlauf_karte.titel_label.setText("Tagesverlauf je Standort")

        monate = []
        for periode, gruppe in df.groupby(df.index.to_period("M")):
            monate.append((periode.start_time.date(), float(gruppe["wert"].sum()), bool(gruppe["ist"].all())))
        self.balken.zeichnen(monate, t.standort[s])
        self.monate_karte.titel_label.setText(
            f"Personentage je Monat – {DEUTSCHE_MONATE[von.month - 1]} {von.year} bis {DEUTSCHE_MONATE[bis.month - 1]} {bis.year}")

        ende = min(bis, ds.letzter_tag)
        haus_df = ds.pivot.haeuser.loc[pd.Timestamp(von):pd.Timestamp(ende)]
        zeilen = []
        for h, st in sorted(ds.pivot.haus_standort.items()):
            if s not in (GESAMT, st) or haus_df.empty or not haus_df[h].any():
                continue
            zeilen.append([h, STANDORT_LABEL[st], zahl(float(haus_df[h].iloc[-1])), zahl(float(haus_df[h].mean())),
                           zahl(float(haus_df[h].max()))])
        self.haeuser.fuellen(zeilen)
        self.haeuser.hoehe_anpassen(12)
        self.haus_karte.untertitel(f"Belegung laut Pivot (nur Reha), Stand {ende:%d.%m.%Y}")

        historie = ds.reha(s)[: pd.Timestamp(ds.stichtag)]
        historie = historie[historie.index >= historie.index[-1] - pd.Timedelta(days=4 * 365)]
        self.heatmap.zeichnen(historie, t.standort[s])
