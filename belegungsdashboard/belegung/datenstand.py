"""Datenmodell und alle fachlichen Aggregationen (ohne Qt).

Belegung eines Standorts an einem Tag =
    Reha (Pivot)
  + Listen-Einträge, die an dem Tag laufen (Mieter, Gäste, DRK, Landkreis, UWT, Pflegeschule)
  + geplante Anreisen – nur für Tage nach dem Stichtag (davor stehen sie schon in der Pivot)
  + bei Brutto zusätzlich FRAI, Jugendhilfe und "andere Bereiche"
    (= Brutto- minus Netto-Kapazität, soweit nicht durch FRAI/Jugendhilfe erklärt)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .konfig import (
    GESAMT, KATEGORIE_ANDERE, KATEGORIE_ANREISE, KATEGORIEN_BRUTTO_ZUSATZ, KATEGORIEN_NETTO, STANDORTE,
)
from .pivot import Pivotdaten
from .prognose import Prognose


@dataclass
class Eintrag:
    kategorie: str
    standort: str
    von: date
    bis: date
    anzahl: int
    bezeichnung: str = ""
    quelle: str = "manuell"         # manuell | mieten | anreisen | uwt
    nur_termin: bool = False        # Anreise ohne Abreise: zählt nicht zur Belegung
    gruppe: str = ""                # Maßnahme/Klasse; bei Personen die namensfreie Bezeichnung

    @property
    def oeffentlich(self) -> str:
        """Bezeichnung ohne Personennamen – für Export und externe Sprachmodelle."""
        return self.gruppe or self.bezeichnung

    @staticmethod
    def aus_dict(d: dict, quelle: str) -> "Eintrag":
        return Eintrag(
            kategorie=d.get("kategorie") or d.get("typ") or "Sonstige",
            standort=d["standort"],
            von=date.fromisoformat(str(d["von"])[:10]),
            bis=date.fromisoformat(str(d["bis"])[:10]),
            anzahl=int(d.get("anzahl", 0) or 0),
            bezeichnung=d.get("bezeichnung", "") or "",
            quelle=quelle,
            nur_termin=bool(d.get("nur_termin", False)),
            gruppe=d.get("gruppe", "") or "",
        )


@dataclass
class Aufschluesselung:
    teile: dict[str, float]          # Kategorie -> Personen (ohne "frei")
    belegt: float
    kapazitaet: int

    @property
    def frei(self) -> float:
        return max(self.kapazitaet - self.belegt, 0.0)

    @property
    def anteil(self) -> float | None:
        return self.belegt / self.kapazitaet if self.kapazitaet > 0 else None


@dataclass
class Datenstand:
    pivot: Pivotdaten
    eintraege: list[Eintrag]
    kapazitaeten: dict[str, dict[str, int]]
    quelle: Path | None = None
    geladen_am: datetime = field(default_factory=datetime.now)
    pivot_aktualisiert: bool | None = None   # None = kein Refresh versucht
    importe: dict[str, dict] = field(default_factory=dict)   # art -> Metadaten des Imports
    prognose: Prognose | None = None
    hinweise: list[str] = field(default_factory=list)
    erinnerungen: list = field(default_factory=list)   # fällige Abreise-Erinnerungen (anreiseliste.Person)

    # ---- Grunddaten --------------------------------------------------------------------

    @property
    def stichtag(self) -> date:
        return self.pivot.stichtag

    @property
    def erster_tag(self) -> date:
        return self.pivot.reha.index[0].date()

    @property
    def letzter_tag(self) -> date:
        return self.pivot.reha.index[-1].date()

    def kapazitaet(self, standort: str, brutto: bool = False) -> int:
        schluessel = "brutto" if brutto else "netto"
        if standort == GESAMT:
            return sum(self.kapazitaeten.get(s, {}).get(schluessel, 0) for s in STANDORTE)
        return int(self.kapazitaeten.get(standort, {}).get(schluessel, 0))

    def hat_kapazitaet(self, standort: str) -> bool:
        return self.kapazitaet(standort) > 0

    def reha(self, standort: str) -> pd.Series:
        if standort == GESAMT:
            return self.pivot.reha[STANDORTE].sum(axis=1)
        return self.pivot.reha[standort]

    # ---- Tagesreihen -------------------------------------------------------------------

    def kategorien(self, standort: str, von: date, bis: date, brutto: bool = False) -> pd.DataFrame:
        """Tage x Kategorien (Personen). Bei GESAMT die Summe der Standorte."""
        if standort == GESAMT:
            teile = [self.kategorien(s, von, bis, brutto) for s in STANDORTE]
            return pd.concat(teile).groupby(level=0).sum().reindex(teile[0].index).fillna(0.0)[
                _spalten_sortiert(set().union(*[t.columns for t in teile]))]

        index = pd.date_range(von, bis, freq="D")
        df = pd.DataFrame(index=index)
        df["Reha"] = self.pivot.reha[standort].reindex(index, fill_value=0.0)
        stichtag = pd.Timestamp(self.stichtag)
        kategorien = set(KATEGORIEN_NETTO) | {KATEGORIE_ANREISE}
        if brutto:
            kategorien |= set(KATEGORIEN_BRUTTO_ZUSATZ)
        for e in self.eintraege:
            if e.standort != standort or e.kategorie not in kategorien or e.nur_termin:
                continue
            start = pd.Timestamp(max(e.von, von))
            ende = pd.Timestamp(min(e.bis, bis))
            if e.kategorie == KATEGORIE_ANREISE:
                start = max(start, stichtag + pd.Timedelta(days=1))
            if start > ende:
                continue
            if e.kategorie not in df:
                df[e.kategorie] = 0.0
            df.loc[start:ende, e.kategorie] += e.anzahl
        if brutto:
            differenz = self.kapazitaet(standort, True) - self.kapazitaet(standort, False)
            erklaert = sum(df[k] for k in KATEGORIEN_BRUTTO_ZUSATZ if k in df) if any(
                k in df for k in KATEGORIEN_BRUTTO_ZUSATZ) else 0.0
            andere = np.maximum(differenz - erklaert, 0.0)
            if np.any(np.asarray(andere) > 0):
                df[KATEGORIE_ANDERE] = andere
        df = df.loc[:, (df != 0).any(axis=0) | (df.columns == "Reha")]
        return df[_spalten_sortiert(df.columns)]

    def belegung(self, standort: str, von: date, bis: date, brutto: bool = False) -> pd.Series:
        return self.kategorien(standort, von, bis, brutto).sum(axis=1)

    def aufschluesselung(self, standort: str, tag: date, brutto: bool = False) -> Aufschluesselung:
        zeile = self.kategorien(standort, tag, tag, brutto).iloc[0]
        teile = {k: float(v) for k, v in zeile.items() if v}
        return Aufschluesselung(teile, float(zeile.sum()), self.kapazitaet(standort, brutto))

    def ist_ist(self, tag: date) -> bool:
        return tag <= self.stichtag

    def verlauf(self, standort: str, von: date, bis: date, brutto: bool = False) -> pd.DataFrame:
        """Tageswerte mit Spalten wert, lo80, hi80, gesichert, ist (bool).

        Bis zum Stichtag: Ist-Belegung. Danach: Reha-Prognose des Monats plus die an dem Tag
        laufenden Verträge (Mieter, Gäste, …). Anreisen stecken bereits in der Prognose
        (als Untergrenze) und werden deshalb nicht noch einmal addiert.
        """
        kat = self.kategorien(standort, von, bis, brutto)
        stichtag = pd.Timestamp(self.stichtag)
        ist = kat.index <= stichtag
        vertraege = kat.drop(columns=[c for c in ("Reha", KATEGORIE_ANREISE) if c in kat]).sum(axis=1)
        gesichert = kat.sum(axis=1)
        df = pd.DataFrame({"wert": gesichert, "lo80": gesichert, "hi80": gesichert,
                           "gesichert": gesichert, "ist": ist}, index=kat.index)
        if self.prognose is not None and (~ist).any():
            werte = [w for w in self.prognose.werte.get(standort, []) if w.art != "ist"]
            if werte:
                # Monatswerte als Stützstellen zur Monatsmitte, dazwischen linear – statt
                # Treppenstufen an jedem Monatswechsel. Laufender Monat: Modellwert der Resttage.
                anker = np.array([np.datetime64(w.monat, "D") + 14 for w in werte]).astype(float)
                niveau = np.array([w.modell if (w.art == "laufend" and w.modell is not None) else w.erwartet
                                   for w in werte])
                unten = np.array([w.erwartet - w.lo80 for w in werte])
                oben = np.array([w.hi80 - w.erwartet for w in werte])
                if werte[0].art == "laufend":  # Band im laufenden Monat nicht künstlich schmal
                    if len(werte) > 1:
                        unten[0], oben[0] = unten[1] * 0.5, oben[1] * 0.5
                zukunft = kat.index[~ist]
                x = zukunft.to_numpy().astype("datetime64[D]").astype(float)
                v = vertraege.loc[zukunft].to_numpy()
                spalten = ["Reha"] + ([KATEGORIE_ANREISE] if KATEGORIE_ANREISE in kat else [])
                bestand_tag = kat.loc[zukunft, spalten].sum(axis=1).to_numpy()
                reha = np.maximum(np.interp(x, anker, niveau), bestand_tag)
                df.loc[zukunft, "wert"] = reha + v
                df.loc[zukunft, "lo80"] = np.maximum(reha - np.interp(x, anker, unten), 0) + v
                df.loc[zukunft, "hi80"] = reha + np.interp(x, anker, oben) + v
        return df

    def monatsprognose(self, standort: str, monat: date, brutto: bool = False) -> dict | None:
        """Gesamtbelegung eines Monats (Reha-Prognose + Verträge) inkl. Band und Kapazität."""
        if self.prognose is None:
            return None
        w = next((x for x in self.prognose.werte.get(standort, []) if x.monat == monat), None)
        if w is None:
            return None
        vertraege = self.vertragsbestand_monat(standort, monat, brutto)
        kap = self.kapazitaet(standort, brutto)
        erwartet = w.erwartet + vertraege
        return {
            "monat": monat, "art": w.art, "erwartet": erwartet, "reha": w.erwartet, "vertraege": vertraege,
            "lo80": w.lo80 + vertraege, "hi80": w.hi80 + vertraege,
            "lo95": w.lo95 + vertraege, "hi95": w.hi95 + vertraege,
            "gesichert": (w.gesichert + vertraege) if w.gesichert is not None else None,
            "ist": w.ist, "kapazitaet": kap, "anteil": erwartet / kap if kap else None,
            "anteil_hi80": (w.hi80 + vertraege) / kap if kap else None,
        }

    # ---- Häuser, Listen ------------------------------------------------------------------

    def haeuser_am(self, standort: str, tag: date) -> list[tuple[str, float]]:
        ts = pd.Timestamp(tag)
        if ts not in self.pivot.haeuser.index:
            return []
        zeile = self.pivot.haeuser.loc[ts]
        return sorted(
            ((h, float(zeile[h])) for h, s in self.pivot.haus_standort.items()
             if standort in (GESAMT, s)),
            key=lambda x: x[0],
        )

    def eintraege_von(self, quelle: str | None = None, kategorie: str | None = None) -> list[Eintrag]:
        return [e for e in self.eintraege
                if (quelle is None or e.quelle == quelle) and (kategorie is None or e.kategorie == kategorie)]

    def anreisen(self, standort: str, von: date, bis: date) -> list[Eintrag]:
        return sorted(
            (e for e in self.eintraege if e.kategorie == KATEGORIE_ANREISE and von <= e.von <= bis
             and standort in (GESAMT, e.standort)),
            key=lambda e: e.von,
        )

    def aktive(self, kategorie: str, standort: str, tag: date) -> list[Eintrag]:
        return [e for e in self.eintraege if e.kategorie == kategorie and e.von <= tag <= e.bis
                and standort in (GESAMT, e.standort)]

    # ---- Zusatzbestand für die Prognose ------------------------------------------------

    def anreise_bestand(self) -> pd.DataFrame:
        """Tageswerte je Standort der geplanten Anreisen nach dem Stichtag (für die Prognose)."""
        ende = pd.Timestamp(self.stichtag) + pd.DateOffset(years=4)
        index = pd.date_range(pd.Timestamp(self.stichtag) + pd.Timedelta(days=1), ende, freq="D")
        df = pd.DataFrame(0.0, index=index, columns=STANDORTE)
        for e in self.eintraege:
            if e.kategorie != KATEGORIE_ANREISE or e.nur_termin or e.standort not in df:
                continue
            start, stop = max(pd.Timestamp(e.von), index[0]), min(pd.Timestamp(e.bis), index[-1])
            if start <= stop:
                df.loc[start:stop, e.standort] += e.anzahl
        return df

    def vertragsbestand_monat(self, standort: str, monat: date, brutto: bool = False) -> float:
        """Ø belegte Plätze durch Listen-Einträge (ohne Reha/Anreisen) in einem Monat."""
        ende = (pd.Timestamp(monat) + pd.offsets.MonthEnd(0)).date()
        df = self.kategorien(standort, monat, ende, brutto)
        spalten = [c for c in df.columns if c not in ("Reha", KATEGORIE_ANREISE)]
        return float(df[spalten].sum(axis=1).mean()) if spalten else 0.0


_REIHENFOLGE = ["Reha", KATEGORIE_ANREISE, "DRK", "Landkreis", "UWT", "Pflegeschule", "Mieter", "Gäste",
                "FRAI", "Jugendhilfe", KATEGORIE_ANDERE]


def _spalten_sortiert(spalten) -> list[str]:
    spalten = list(spalten)
    return sorted(spalten, key=lambda c: (_REIHENFOLGE.index(c) if c in _REIHENFOLGE else 99, c))


def zeitraum_text(von: date, bis: date) -> str:
    if von == bis:
        return von.strftime("%d.%m.%Y")
    return f"{von:%d.%m.%Y} – {bis:%d.%m.%Y}"


def tage_zwischen(von: date, bis: date) -> int:
    return (bis - von).days + 1


def vorwoche(tag: date) -> date:
    return tag - timedelta(days=7)
