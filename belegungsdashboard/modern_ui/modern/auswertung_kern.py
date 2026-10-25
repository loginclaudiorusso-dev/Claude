"""Daten der Auswertung (Lage, Belegung im Zeitraum, Prognose) aus dem Datenstand des Hauptprogramms – Pivot,
Listen, Kapazitäten, Prognose-Modelle. Ohne NiceGUI. Der Datenstand wird zwischengespeichert, bis sich eine
Quelle ändert (die Prognose rechnet einige Sekunden)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import konfig, speicher

MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
STANDORTE = {konfig.GESAMT: konfig.STANDORT_LABEL[konfig.GESAMT],
             **{s: konfig.STANDORT_LABEL[s] for s in konfig.STANDORTE}}

_ZWISCHEN: dict = {"schluessel": None, "ds": None, "fehler": ""}
_SPERRE = threading.Lock()


def monat_text(m: date) -> str:
    return f"{MONATE[m.month - 1]} {m.year}"


def _schluessel():
    from belegung import laden

    quelle = laden.excel_suchen()
    teile = [str(quelle), quelle.stat().st_mtime if quelle and quelle.exists() else 0]
    from belegung import anreiseliste, uwt

    for name in (speicher.MANUELLE_EINTRAEGE, speicher.KAPAZITAETEN, speicher.PIVOT_PROFILE, anreiseliste.DATEI, uwt.DATEI,
                 f"{speicher.IMPORT_ORDNER}/anreisen.json", f"{speicher.IMPORT_ORDNER}/mieten.json"):
        p = speicher.pfad(name)
        teile.append(p.stat().st_mtime if p.exists() else 0)
    return quelle, tuple(teile)


def datenstand(neu: bool = False):
    """(Datenstand oder None, Fehlertext). Lädt nur neu, wenn sich Pivot, Listen oder Kapazitäten geändert haben."""
    from belegung import laden

    with _SPERRE:
        quelle, schluessel = _schluessel()
        if not neu and schluessel == _ZWISCHEN["schluessel"]:
            return _ZWISCHEN["ds"], _ZWISCHEN["fehler"]
        if quelle is None:
            ds, fehler = None, ("Keine Pivot-Datei gefunden. Unter „Daten & Import → Pivot“ die Excel-Datei mit der "
                                "Belegungs-Pivot wählen.")
        else:
            try:
                ds, fehler = laden.lade(quelle), ""
            except Exception as exc:       # noqa: BLE001 – Fehler sichtbar machen
                ds, fehler = None, f"Die Pivot-Datei „{quelle.name}“ konnte nicht gelesen werden: {exc}"
        _ZWISCHEN.update(schluessel=schluessel, ds=ds, fehler=fehler)
        return ds, fehler


def _f(x) -> float:
    return float(x) if x is not None else 0.0


# ---------------------------------------------------------------------------------------
# Lage heute + Verlauf
# ---------------------------------------------------------------------------------------

@dataclass
class Lage:
    stichtag: date
    belegt: float
    kapazitaet: int
    teile: dict
    haeuser: list
    verlauf: dict                 # tage, ist, prognose, lo80, hi80
    hinweise: list = field(default_factory=list)
    anreisen: list = field(default_factory=list)   # nächste 21 Tage: (Datum, Standort, Anzahl, Bezeichnung)

    @property
    def anteil(self) -> float | None:
        return self.belegt / self.kapazitaet if self.kapazitaet else None


def lage(ds, standort: str, brutto: bool, zurueck: int = 120, vor: int = 180) -> Lage:
    tag = ds.stichtag
    a = ds.aufschluesselung(standort, tag, brutto)
    v = ds.verlauf(standort, tag - timedelta(days=zurueck), tag + timedelta(days=vor), brutto)
    tage = [d.strftime("%Y-%m-%d") for d in v.index]
    ist = [round(_f(w), 1) if i else None for w, i in zip(v["wert"], v["ist"])]
    prog = [round(_f(w), 1) if not i else None for w, i in zip(v["wert"], v["ist"])]
    lo = [round(_f(w), 1) if not i else None for w, i in zip(v["lo80"], v["ist"])]
    hi = [round(_f(w), 1) if not i else None for w, i in zip(v["hi80"], v["ist"])]
    return Lage(tag, a.belegt, a.kapazitaet, dict(sorted(a.teile.items(), key=lambda x: -x[1])),
                ds.haeuser_am(standort, tag), {"tage": tage, "ist": ist, "prognose": prog, "lo80": lo, "hi80": hi},
                list(ds.hinweise), [(e.von, konfig.STANDORT_LABEL.get(e.standort, e.standort), e.anzahl, e.bezeichnung or "–")
                                    for e in ds.anreisen(standort, date.today(), date.today() + timedelta(days=20))])


# ---------------------------------------------------------------------------------------
# Belegung im Zeitraum
# ---------------------------------------------------------------------------------------

@dataclass
class Zeitraum:
    von: date
    bis: date
    tage: int
    personentage: dict            # Kategorie → Personentage
    mittel: float
    hoechst: float
    hoechst_tag: date | None
    kapazitaet: int
    anreisen: int

    @property
    def gesamt(self) -> float:
        return sum(self.personentage.values())


def zeitraum(ds, standort: str, von: date, bis: date, brutto: bool) -> Zeitraum:
    if bis < von:
        von, bis = bis, von
    k = ds.kategorien(standort, von, bis, brutto)
    summe = k.sum(axis=1)
    pt = {c: round(float(k[c].sum()), 1) for c in k.columns if float(k[c].sum())}
    return Zeitraum(von, bis, len(k), dict(sorted(pt.items(), key=lambda x: -x[1])), float(summe.mean()) if len(k) else 0.0,
                    float(summe.max()) if len(k) else 0.0, summe.idxmax().date() if len(k) else None,
                    ds.kapazitaet(standort, brutto), len(ds.anreisen(standort, von, bis)))


# ---------------------------------------------------------------------------------------
# Prognose
# ---------------------------------------------------------------------------------------

@dataclass
class PZeile:
    monat: date
    art: str
    erwartet: float
    lo80: float
    hi80: float
    lo95: float
    hi95: float
    gesichert: float | None
    ist: float | None
    vertraege: float = 0.0


@dataclass
class Prognose:
    zeilen: list[PZeile]
    kapazitaet: int
    modell: str
    beschreibung: str
    mae_1m: float | None
    mae: float | None
    abdeckung80: float | None
    kandidaten: list
    rueckblick: list              # (Monat, Ist, Prognose)
    monate_historie: int = 0


def prognose(ds, standort: str, brutto: bool, zurueck: int = 24, vor: int = 24) -> Prognose | None:
    if ds.prognose is None:
        return None
    import pandas as pd

    start = date(ds.stichtag.year, ds.stichtag.month, 1)
    zeilen = []
    for i in range(-zurueck, vor):
        m = (pd.Timestamp(start) + pd.DateOffset(months=i)).date()
        mp = ds.monatsprognose(standort, m, brutto)
        if mp:
            zeilen.append(PZeile(m, mp["art"], _f(mp["erwartet"]), _f(mp["lo80"]), _f(mp["hi80"]), _f(mp["lo95"]),
                                 _f(mp["hi95"]), _f(mp["gesichert"]) if mp["gesichert"] is not None else None,
                                 _f(mp["ist"]) if mp["ist"] is not None else None, _f(mp["vertraege"])))
    m = ds.prognose.modelle.get(standort)
    if m is None:
        return Prognose(zeilen, ds.kapazitaet(standort, brutto), "", "", None, None, None, [], [])
    rueck = [(mon, float(ist), float(p)) for mon, ist, p in (m.rueckblick or [])]
    return Prognose(zeilen, ds.kapazitaet(standort, brutto), m.name, m.beschreibung, m.mae_1m, m.mae, m.abdeckung80,
                    list(m.kandidaten or []), rueck, getattr(m, "monate_historie", 0) or 0)


def einschaetzung(hi80: float, kapazitaet: int) -> tuple[str, str]:
    """(Stufe ok|knapp|kritisch|ueber|unbekannt, Text) nach der oberen 80 %-Grenze."""
    if not kapazitaet:
        return "unbekannt", "Kapazität fehlt"
    stufe, text = konfig.ampel_stufe(hi80 / kapazitaet)
    return stufe, f"{text} · {round(100 * hi80 / kapazitaet)} %"


# ---------------------------------------------------------------------------------------
# Belegung im Zeitraum – Einzelheiten wie im bisherigen Programm (Tagesverlauf, Monate, Häuser, Muster)
# ---------------------------------------------------------------------------------------

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


@dataclass
class BDetails:
    tage: list[str]                   # „TT.MM.“ je Tag
    ist: list[bool]                   # Ist-Wert (sonst Prognose)
    kategorien: dict[str, list[float]]  # Belegungsart → Werte je Tag (Zukunft: Reha = Prognose)
    tiefst: float
    tiefst_tag: date | None
    auslastung: float | None          # Ø Auslastung (0–1)
    spitze: float | None              # höchste Auslastung (0–1)
    monate: list[tuple[str, float, bool]]   # (Monat, Personentage, nur Ist)
    haeuser: list[tuple[str, str, float, float, float]]   # Haus, Standort, zuletzt, Ø, Höchst
    haeuser_stand: date | None
    muster: list[list[float | None]]  # 7 Wochentage × 12 Monate: Ø Ist-Belegung (letzte 4 Jahre)


def belegung_details(ds, standort: str, von: date, bis: date, brutto: bool) -> BDetails:
    import pandas as pd

    if bis < von:
        von, bis = bis, von
    von = max(von, ds.erster_tag)
    df = ds.verlauf(standort, von, bis, brutto)
    w = df["wert"]
    kap = ds.kapazitaet(standort, brutto)
    ist = df["ist"].to_numpy()
    kat = ds.kategorien(standort, von, bis, brutto)
    if (~ist).any():                     # Zukunft: Reha durch die Prognose ersetzen (wie im Hauptprogramm)
        kat = kat.copy()
        andere = kat.drop(columns=["Reha"] + (["Anreise"] if "Anreise" in kat else [])).sum(axis=1)
        kat.loc[~ist, "Reha"] = (df["wert"] - andere)[~ist]
        if "Anreise" in kat:
            kat.loc[~ist, "Anreise"] = 0
    kategorien = {str(c): [round(float(x), 1) for x in kat[c].to_numpy()] for c in kat.columns if float(kat[c].abs().sum())}
    monate = []
    for periode, gruppe in df.groupby(df.index.to_period("M")):
        monate.append((f"{MONATE[periode.month - 1]} {str(periode.year)[2:]}", round(float(gruppe["wert"].sum())),
                       bool(gruppe["ist"].all())))
    ende = min(bis, ds.letzter_tag)
    haeuser = []
    if ende >= von:
        hdf = ds.pivot.haeuser.loc[pd.Timestamp(von):pd.Timestamp(ende)]
        for h, st in sorted(ds.pivot.haus_standort.items()):
            if standort not in (konfig.GESAMT, st) or hdf.empty or not hdf[h].any():
                continue
            haeuser.append((h, konfig.STANDORT_LABEL[st], float(hdf[h].iloc[-1]), float(hdf[h].mean()), float(hdf[h].max())))
    historie = ds.reha(standort)[: pd.Timestamp(ds.stichtag)]
    muster: list[list[float | None]] = [[None] * 12 for _ in range(7)]
    if len(historie):
        historie = historie[historie.index >= historie.index[-1] - pd.Timedelta(days=4 * 365)]
        hd = pd.DataFrame({"w": historie.to_numpy(dtype=float), "m": historie.index.month, "d": historie.index.weekday})
        pv = hd.pivot_table(index="d", columns="m", values="w", aggfunc="mean").reindex(index=range(7), columns=range(1, 13))
        muster = [[None if pd.isna(x) else round(float(x), 1) for x in zeile] for zeile in pv.to_numpy()]
    return BDetails([f"{t:%d.%m.}" for t in w.index], [bool(x) for x in ist], kategorien,
                    float(w.min()) if len(w) else 0.0, w.idxmin().date() if len(w) else None,
                    float(w.mean()) / kap if kap and len(w) else None, float(w.max()) / kap if kap and len(w) else None,
                    monate, haeuser, ende if haeuser else None, muster)
