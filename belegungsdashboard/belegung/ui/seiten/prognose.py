"""Prognose: Monatsverlauf mit Bändern, Kapazitätscheck mit Was-wäre-wenn, Modellgüte."""

from __future__ import annotations

from datetime import date

import pandas as pd
from PySide6.QtWidgets import QCheckBox, QGridLayout, QHBoxLayout, QSpinBox, QWidget

from ...konfig import GESAMT, STANDORT_LABEL, STANDORTE, ampel_stufe
from ...prognose import BACKTEST_URSPRUENGE
from .. import theme
from ..basis import Seite, Zustand
from ..charts import MonatsChart
from ..widgets import DEUTSCHE_MONATE, Karte, KpiKarte, Pille, Segment, Tabelle, label, prozent, zahl


def _monat(m: date) -> str:
    return f"{DEUTSCHE_MONATE[m.month - 1]} {m.year}"


class PrognoseSeite(Seite):
    titel = "Prognose"
    untertitel = "Erwartete Belegung je Monat – mit ehrlicher Unsicherheit"

    def __init__(self, zustand: Zustand):
        super().__init__(zustand)
        kpis = QGridLayout()
        kpis.setSpacing(16)
        self.k_naechster = KpiKarte("Nächster Monat", sparkline=False)
        self.k_spitze = KpiKarte("Höchste Auslastung (12 Monate)", sparkline=False)
        self.k_fehler = KpiKarte("Ø Fehler 1 Monat voraus", sparkline=False)
        self.k_treffer = KpiKarte("Treffer 80 %-Spanne", sparkline=False)
        for i, k in enumerate((self.k_naechster, self.k_spitze, self.k_fehler, self.k_treffer)):
            kpis.addWidget(k, 0, i)
            kpis.setColumnStretch(i, 1)
        self.lay.addLayout(kpis)

        self.chart_karte = Karte("Monatsverlauf", "Ø belegte Plätze je Monat (Reha + Verträge)")
        steuer = QHBoxLayout()
        steuer.setSpacing(14)
        self.cb95 = QCheckBox("95 %-Spanne")
        self.cb95.setChecked(True)
        self.cb_rueck = QCheckBox("Backtest zeigen")
        self.cb_rueck.setToolTip("Was das Modell in den letzten Monaten jeweils einen Monat vorher vorhergesagt hätte")
        for cb in (self.cb95, self.cb_rueck):
            cb.toggled.connect(lambda _b: self.anstossen())
            steuer.addWidget(cb)
        self.horizont = Segment(["12 M", "24 M", "36 M"], 1)
        self.horizont.geaendert.connect(lambda _i: self.anstossen())
        steuer.addWidget(self.horizont)
        w = QWidget()
        w.setLayout(steuer)
        self.chart_karte.aktion(w)
        self.chart = MonatsChart(hoehe=3.7)
        self.chart_karte.inhalt.addWidget(self.chart)
        self.lay.addWidget(self.chart_karte)

        self.tab_karte = Karte("Reicht die Kapazität?", "Einschätzung nach der oberen 80 %-Grenze (vorsichtige Planung)")
        wenn = QHBoxLayout()
        wenn.setSpacing(8)
        wenn.addWidget(label("Was wäre, wenn die Kapazität", "muted"))
        self.wenn = QSpinBox()
        self.wenn.setRange(0, 5000)
        self.wenn.setFixedWidth(80)
        self.wenn.setToolTip("Testweise andere Kapazität – wird nicht gespeichert")
        self.wenn.valueChanged.connect(lambda _v: self._tabelle())
        wenn.addWidget(self.wenn)
        wenn.addWidget(label("wäre?", "muted"))
        ww = QWidget()
        ww.setLayout(wenn)
        self.tab_karte.aktion(ww)
        self.tabelle = Tabelle(["Monat", "Erwartet", "80 %-Spanne", "95 %-Spanne", "Gesichert", "Kapazität", "Einschätzung"],
                               ["l", "r", "r", "r", "r", "r", "l"], dehnen=6)
        self.tab_karte.inhalt.addWidget(self.tabelle)
        self.lay.addWidget(self.tab_karte)

        self.modell_karte = Karte("So wurde gerechnet")
        self.modell_text = label("", "muted", umbruch=True)
        self.modell_karte.inhalt.addWidget(self.modell_text)
        self.kandidaten = Tabelle(["Modell (Backtest)", "Ø Fehler 1–12 Monate"], ["l", "r"])
        self.modell_karte.inhalt.addWidget(self.kandidaten)
        self.rueck_karte = Karte("Rückblick: Blind-Prognosen", "Jeweils einen Monat im Voraus gerechnet, nur mit damaligen Daten")
        self.rueck = Tabelle(["Monat", "Ist", "Prognose", "Abweichung"])
        self.rueck_karte.inhalt.addWidget(self.rueck)
        self.zeile(self.modell_karte, self.rueck_karte, stretch=[3, 2])
        self.lay.addStretch()
        self._wenn_standort = None

    def aktualisieren(self) -> None:
        ds, z = self.z.ds, self.z
        if ds.prognose is None:
            self.chart.leer("Prognose wird berechnet …")
            return
        s = z.standort
        kap = ds.kapazitaet(s, z.brutto)
        if self._wenn_standort != (s, z.brutto, kap):
            self._wenn_standort = (s, z.brutto, kap)
            self.wenn.blockSignals(True)
            self.wenn.setValue(kap)
            self.wenn.blockSignals(False)
        self._kpis()
        self._chart()
        self._tabelle()
        self._modell()

    def _zeilen(self, monate_zurueck: int, monate_vor: int) -> list[dict]:
        ds, z = self.z.ds, self.z
        start = date(ds.stichtag.year, ds.stichtag.month, 1)
        monate = [(pd.Timestamp(start) + pd.DateOffset(months=i)).date() for i in range(-monate_zurueck, monate_vor)]
        return [mp for m in monate if (mp := ds.monatsprognose(z.standort, m, z.brutto))]

    def _kpis(self) -> None:
        ds, z = self.z.ds, self.z
        zukunft = [m for m in self._zeilen(0, 13) if m["art"] == "prognose"]
        if zukunft:
            n = zukunft[0]
            self.k_naechster.titel.setText(f"Erwartet {_monat(n['monat'])}")
            self.k_naechster.wert.setText(zahl(n["erwartet"]))
            self.k_naechster.detail.setText(f"80 %: {zahl(n['lo80'])} – {zahl(n['hi80'])} · gesichert {zahl(n['gesichert'])}")
        spitze = max((m for m in zukunft[:12] if m["anteil_hi80"]), key=lambda m: m["anteil_hi80"], default=None)
        if spitze:
            stufe, text = ampel_stufe(spitze["anteil_hi80"])
            self.k_spitze.wert.setText(prozent(spitze["anteil_hi80"]))
            self.k_spitze.pille.setzen(stufe, text)
            self.k_spitze.pille.setVisible(True)
            self.k_spitze.detail.setText(f"{_monat(spitze['monat'])}, vorsichtig geschätzt")
        else:
            self.k_spitze.wert.setText("–")
            self.k_spitze.pille.setVisible(False)
            self.k_spitze.detail.setText("Kapazität nicht hinterlegt")
        m = ds.prognose.modelle.get(z.standort)
        self.k_fehler.wert.setText(f"± {zahl(m.mae_1m, 1)}" if m and m.mae_1m is not None else "–")
        self.k_fehler.detail.setText(f"Personen · 12 Monate voraus: ± {zahl(m.mae, 1)}" if m and m.mae else "")
        self.k_fehler.setToolTip("Mittlere Abweichung der Blind-Prognosen im Backtest (Monatsmittel, Personen)")
        self.k_treffer.wert.setText(prozent(m.abdeckung80) if m and m.abdeckung80 is not None else "–")
        self.k_treffer.detail.setText("Backtest-Fälle innerhalb (Soll 80 %)")

    def _chart(self) -> None:
        ds, z, t = self.z.ds, self.z, theme.T
        vor = [12, 24, 36][self.horizont.index()]
        zeilen = self._zeilen(24, vor)
        rueck = None
        if self.cb_rueck.isChecked():
            m = ds.prognose.modelle.get(z.standort)
            if m and m.rueckblick:
                zusatz = {r["monat"]: r["vertraege"] for r in zeilen}
                rueck = [(mon, ist, p + zusatz.get(mon, 0.0)) for mon, ist, p in m.rueckblick]
            elif z.standort == GESAMT:
                self.z.meldung.emit("Den Backtest gibt es je Standort – bitte einen Standort wählen.", "info")
        self.chart.zeichnen(zeilen, t.standort[z.standort], ds.kapazitaet(z.standort, z.brutto) or None,
                            band95=self.cb95.isChecked(), rueckblick=rueck)
        self.chart_karte.titel_label.setText(f"Monatsverlauf {STANDORT_LABEL[z.standort]}")

    def _tabelle(self) -> None:
        if self.z.ds is None or self.z.ds.prognose is None:
            return
        kap = self.wenn.value()
        zeilen = []
        for mp in self._zeilen(0, [12, 24, 36][self.horizont.index()]):
            if kap:
                stufe, text = ampel_stufe(mp["hi80"] / kap)
                pille = Pille(f"{text} · {prozent(mp['hi80'] / kap)}", stufe)
                zelle = QWidget()
                h = QHBoxLayout(zelle)
                h.setContentsMargins(8, 0, 0, 0)
                h.addWidget(pille)
                h.addStretch()
            else:
                zelle = "Kapazität fehlt"
            name = _monat(mp["monat"]) + (" (laufend)" if mp["art"] == "laufend" else "")
            zeilen.append([name, zahl(mp["erwartet"]), f"{zahl(mp['lo80'])} – {zahl(mp['hi80'])}",
                           f"{zahl(mp['lo95'])} – {zahl(mp['hi95'])}",
                           zahl(mp["gesichert"]) if mp["gesichert"] is not None else "–", zahl(kap) if kap else "–", zelle])
        self.tabelle.fuellen(zeilen)
        self.tabelle.hoehe_anpassen(13)
        echte = self.z.ds.kapazitaet(self.z.standort, self.z.brutto)
        self.tab_karte.untertitel(
            "Einschätzung nach der oberen 80 %-Grenze (vorsichtige Planung)"
            + (f" · Testweise mit {zahl(kap)} statt {zahl(echte)} Plätzen gerechnet – nicht gespeichert" if kap != echte else ""))

    def _modell(self) -> None:
        ds, z = self.z.ds, self.z
        m = ds.prognose.modelle.get(z.standort)
        if m is None:
            return
        if z.standort == GESAMT:
            text = (f"<b>Gesamt</b> ist die Summe der drei Standortprognosen ({m.beschreibung.split(': ', 1)[-1]}). "
                    "Die Spanne kommt aus den tatsächlichen Backtest-Fehlern der Summe – dadurch ist berücksichtigt, "
                    "dass die Standorte sich gegenseitig beeinflussen.")
            self.kandidaten.fuellen([[STANDORT_LABEL[s], zahl(ds.prognose.modelle[s].mae, 1) if ds.prognose.modelle[s].mae else "–"]
                                     for s in STANDORTE])
            self.kandidaten.setHorizontalHeaderLabels(["Standort", "Ø Fehler 1–12 Monate"])
        else:
            text = (f"Gewählt: <b>{m.name}</b> – {m.beschreibung}. Grundlage: {m.monate_historie} abgeschlossene Monate "
                    f"ab {_monat(m.start_monat) if m.start_monat else '–'}. Alle Kandidaten wurden für die letzten "
                    f"{BACKTEST_URSPRUENGE} Monate blind gerechnet (nur mit Daten, die zum jeweiligen Zeitpunkt vorlagen); "
                    "gewählt wurde das Modell mit dem kleinsten mittleren Fehler. Die Spanne wächst mit dem Abstand zur "
                    "Gegenwart und ist so kalibriert, dass im Backtest 80 % der Fälle in der 80 %-Spanne lagen. "
                    "Die Prognose fällt nie unter den bereits gesicherten Bestand laut Pivot (plus importierte Anreisen). "
                    "Mieter, Gäste und sonstige Verträge werden als feste Größe addiert.")
            self.kandidaten.fuellen([[n, zahl(f, 1)] for n, f in m.kandidaten])
            self.kandidaten.setHorizontalHeaderLabels(["Modell (Backtest)", "Ø Fehler 1–12 Monate"])
        self.modell_text.setText(text)
        self.kandidaten.hoehe_anpassen(6)
        if m.rueckblick:
            self.rueck.fuellen([[_monat(mon), zahl(ist), zahl(p), ("+" if p > ist else "−") + zahl(abs(p - ist))]
                                for mon, ist, p in reversed(m.rueckblick)])
        else:
            self.rueck.fuellen([["Nur je Standort verfügbar", "", "", ""]] if z.standort == GESAMT else [])
        self.rueck.hoehe_anpassen(8)
