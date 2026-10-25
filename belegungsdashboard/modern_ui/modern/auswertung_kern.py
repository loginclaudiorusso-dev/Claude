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
    if not rueck and standort == konfig.GESAMT:
        rueck = _rueckblick_summe(ds)
    return Prognose(zeilen, ds.kapazitaet(standort, brutto), m.name, m.beschreibung, m.mae_1m, m.mae, m.abdeckung80,
                    list(m.kandidaten or []), rueck, getattr(m, "monate_historie", 0) or 0)


def _rueckblick_summe(ds) -> list:
    """Backtest für „Gesamt“: Summe der Blind-Prognosen der Standorte (die Gesamtprognose ist deren Summe) –
    nur für Monate, die alle Standorte haben."""
    teile = []
    for s in konfig.STANDORTE:
        m = ds.prognose.modelle.get(s)
        if m is None or not m.rueckblick:
            return []
        teile.append({mon: (float(ist), float(p)) for mon, ist, p in m.rueckblick})
    gemeinsam = sorted(set.intersection(*(set(t) for t in teile)))
    return [(mon, sum(t[mon][0] for t in teile), sum(t[mon][1] for t in teile)) for mon in gemeinsam]


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


# ---------------------------------------------------------------------------------------
# Prognose für Präsentationen: Szenario (Kapazität / Auslastungs-Offset), Kernaussagen, Vorjahresvergleich, Export
# ---------------------------------------------------------------------------------------

@dataclass
class SZeile:
    monat: date
    art: str                      # ist | laufend | prognose
    ist: float | None
    erwartet: float
    lo80: float
    hi80: float
    lo95: float
    hi95: float
    gesichert: float | None
    reserve: float | None         # Kapazität − Erwartet (bzw. Ist)
    stufe: str                    # ok | knapp | kritisch | ueber | unbekannt (nach oberer 80 %-Grenze)
    text: str                     # „Reserve vorhanden · 64 %“ / „Engpass! · 97 %“


def szenario(pg: Prognose, kapazitaet: int, offset: float = 0.0) -> list[SZeile]:
    """Prognose mit testweiser Kapazität und Auslastungs-Offset (±%, wirkt nur auf die Prognose, nicht auf Ist)."""
    f = 1 + offset / 100
    erg = []
    for z in pg.zeilen:
        prog = z.art != "ist"
        e, l8, h8, l9, h9 = ((z.erwartet * f, z.lo80 * f, z.hi80 * f, z.lo95 * f, z.hi95 * f) if prog else
                             (z.erwartet, z.lo80, z.hi80, z.lo95, z.hi95))
        wert = e if prog or z.ist is None else z.ist
        st, tx = einschaetzung(h8 if prog else wert, kapazitaet)
        kurz = {"ok": "Reserve vorhanden", "knapp": "Reserve knapp", "kritisch": "Engpass!", "ueber": "Engpass!"}.get(st, tx)
        prozent = f" · {round(100 * (h8 if prog else wert) / kapazitaet)} %" if kapazitaet else ""
        erg.append(SZeile(z.monat, z.art, z.ist, e, l8, h8, l9, h9, z.gesichert,
                          (kapazitaet - wert) if kapazitaet else None, st, kurz + prozent if kapazitaet else tx))
    return erg


def kernaussagen(pg: Prognose, kapazitaet: int, offset: float = 0.0, monate: int = 12) -> list[str]:
    """Die wichtigsten Aussagen in einem Satz je Punkt – für die Geschäftsführung."""
    zs = [z for z in szenario(pg, kapazitaet, offset) if z.art != "ist"][:monate]
    if not zs:
        return []
    erg = []
    spitze = max(zs, key=lambda z: z.erwartet)
    tief = min(zs, key=lambda z: z.erwartet)
    if kapazitaet:
        erg.append(f"Höchststand voraussichtlich {monat_text(spitze.monat)} mit {round(spitze.erwartet)} Plätzen "
                   f"({round(100 * spitze.erwartet / kapazitaet)} % Auslastung, vorsichtig {round(100 * spitze.hi80 / kapazitaet)} %).")
        eng = [z for z in zs if z.stufe in ("kritisch", "ueber")]
        if eng:
            erg.append(f"Engpass möglich in {len(eng)} von {len(zs)} Monaten – zuerst {monat_text(eng[0].monat)} "
                       f"(obere 80 %-Grenze {round(eng[0].hi80)} von {kapazitaet} Plätzen).")
        else:
            knapp = min(zs, key=lambda z: z.reserve if z.reserve is not None else 0)
            erg.append(f"Reserve in allen {len(zs)} Monaten – am knappsten {monat_text(knapp.monat)} mit "
                       f"{round(knapp.reserve)} freien Plätzen.")
    else:
        erg.append(f"Höchststand voraussichtlich {monat_text(spitze.monat)} mit {round(spitze.erwartet)} Plätzen.")
    erg.append(f"Ruhigster Monat: {monat_text(tief.monat)} mit {round(tief.erwartet)} Plätzen.")
    if pg.abdeckung80 is not None:
        erg.append(f"Trefferquote im Backtest: {round(100 * pg.abdeckung80)} % der Monate lagen in der 80 %-Spanne"
                   + (f", Ø Abweichung einen Monat voraus ± {round(pg.mae_1m)} Platz{'' if round(pg.mae_1m) == 1 else 'e'}."
                      if pg.mae_1m is not None else "."))
    if offset:
        erg.append(f"Szenario: Auslastung {'+' if offset > 0 else '−'}{abs(offset):g} % gegenüber der Prognose.")
    return erg


def jahresvergleich(pg: Prognose) -> dict[int, tuple[list, list]]:
    """Jahr → (Ist je Monat Jan–Dez, Prognose je Monat) – fehlende Monate als None."""
    erg: dict[int, tuple[list, list]] = {}
    for z in pg.zeilen:
        ist, prog = erg.setdefault(z.monat.year, ([None] * 12, [None] * 12))
        if z.art == "ist" and z.ist is not None:
            ist[z.monat.month - 1] = round(z.ist, 1)
        else:
            prog[z.monat.month - 1] = round(z.erwartet, 1)
    for jahr, (ist, prog) in erg.items():           # Prognose an den letzten Ist-Monat anschließen
        letzte = max((i for i, v in enumerate(ist) if v is not None), default=None)
        if letzte is not None and letzte + 1 < 12 and prog[letzte + 1] is not None:
            prog[letzte] = ist[letzte]
    return dict(sorted(erg.items()))


def prognose_export(pg: Prognose, kapazitaet: int, offset: float, standort: str, brutto: bool, art: str = "xlsx") -> str:
    """Prognosedaten als Excel (mit Blatt „Info“) oder CSV in den Export-Ordner. Gibt den Pfad zurück."""
    from pathlib import Path

    import pandas as pd

    zs = szenario(pg, kapazitaet, offset)
    df = pd.DataFrame([{"Monat": monat_text(z.monat), "Art": {"ist": "Ist", "laufend": "laufend"}.get(z.art, "Prognose"),
                        "Ist": None if z.ist is None or z.art != "ist" else round(z.ist, 1), "Erwartet": round(z.erwartet, 1),
                        "80 % unten": round(z.lo80, 1), "80 % oben": round(z.hi80, 1), "95 % unten": round(z.lo95, 1),
                        "95 % oben": round(z.hi95, 1), "Gesichert": None if z.gesichert is None else round(z.gesichert, 1),
                        "Kapazität": kapazitaet or None, "Reserve": None if z.reserve is None else round(z.reserve, 1),
                        "Einschätzung": z.text} for z in zs])
    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Export"))
    ziel.mkdir(parents=True, exist_ok=True)
    name = f"Prognose_{STANDORTE.get(standort, standort).replace(' ', '_')}_{'Brutto' if brutto else 'Netto'}_{date.today():%Y-%m-%d}"
    if art == "csv":
        pfad = ziel / f"{name}.csv"
        df.to_csv(pfad, sep=";", decimal=",", index=False, encoding="utf-8-sig")
        return str(pfad)
    pfad = ziel / f"{name}.xlsx"
    info = pd.DataFrame({"Angabe": ["Standort", "Zählweise", "Kapazität (Szenario)", "Auslastungs-Offset", "Modell",
                                    "Trefferquote 80 %-Spanne", "Erstellt"],
                         "Wert": [STANDORTE.get(standort, standort), "Brutto" if brutto else "Netto", kapazitaet,
                                  f"{offset:+g} %", pg.modell or "–",
                                  f"{round(100 * pg.abdeckung80)} %" if pg.abdeckung80 is not None else "–",
                                  f"{date.today():%d.%m.%Y}"]})
    with pd.ExcelWriter(pfad) as w:
        df.to_excel(w, sheet_name="Prognose", index=False)
        info.to_excel(w, sheet_name="Info", index=False)
        for blatt in w.sheets.values():
            for spalte in blatt.columns:
                blatt.column_dimensions[spalte[0].column_letter].width = max(12, max(len(str(c.value or "")) for c in spalte) + 2)
    return str(pfad)


def png_speichern(daten_url: str, standort: str) -> str:
    """Diagramm-Bild (data:image/png;base64,…) im Export-Ordner ablegen."""
    import base64
    from pathlib import Path

    kopf, _, b64 = daten_url.partition(",")
    if "image/png" not in kopf:
        raise ValueError("Das Diagramm konnte nicht als Bild gelesen werden.")
    ziel = Path(speicher.einstellungen().get("export_ordner") or speicher.pfad("Export"))
    ziel.mkdir(parents=True, exist_ok=True)
    pfad = ziel / f"Prognose_{STANDORTE.get(standort, standort).replace(' ', '_')}_{date.today():%Y-%m-%d}.png"
    pfad.write_bytes(base64.b64decode(b64))
    return str(pfad)
