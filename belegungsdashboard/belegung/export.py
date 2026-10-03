"""JSON für Belegungsdashboard.html im bisherigen Format (Schlüssel wie im VBA-/v3-Export).

Neue Felder kommen nur hinzu; bestehende Schlüssel bleiben, damit das HTML weiter läuft.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import __version__
from .datenstand import Datenstand
from .konfig import GESAMT, STANDORTE

JSON_OEFFNEN = '<script id="__data__" type="application/json">'
JSON_SCHLIESSEN = "</script>"


def _iso_werte(serie: pd.Series) -> dict[str, int]:
    return {ts.strftime("%Y-%m-%d"): int(round(v)) for ts, v in serie.items()}


def _saisonprofile(ds: Datenstand) -> dict:
    ergebnis = {}
    for s in STANDORTE:
        ist = ds.reha(s)[: pd.Timestamp(ds.stichtag)]
        ist = ist[ist.index >= pd.Timestamp(ds.stichtag) - pd.DateOffset(years=4)]
        profil = {}
        for m in range(1, 13):
            w = ist[ist.index.month == m]
            profil[str(m)] = {"mittel": round(float(w.mean()), 2) if len(w) else 0.0, "max": int(w.max()) if len(w) else 0,
                              "std": round(float(w.std()), 2) if len(w) > 1 else 0.0, "n": int(len(w))}
        ergebnis[s] = profil
    return ergebnis


def baue_json(ds: Datenstand) -> dict:
    def liste(kategorie: str) -> list[dict]:
        return [{"von": e.von.isoformat(), "bis": e.bis.isoformat(), "anzahl": e.anzahl, "standort": e.standort,
                 "bezeichnung": e.oeffentlich} for e in ds.eintraege if e.kategorie == kategorie]

    def belegungsliste(kategorien: tuple[str, ...]) -> list[dict]:
        return [{"von": e.von.isoformat(), "bis": e.bis.isoformat(), "standort": e.standort, "bereich": "",
                 "anzahl": e.anzahl, "typ": e.kategorie, "bezeichnung": e.oeffentlich}
                for e in ds.eintraege if e.kategorie in kategorien]

    prognosen, modellinfo = {}, {}
    for s in STANDORTE + [GESAMT]:
        punkte = []
        for w in (ds.prognose.werte.get(s, []) if ds.prognose else []):
            if w.monat < date(ds.stichtag.year - 2, 1, 1):
                continue
            ist = w.art == "ist"
            m15 = date(w.monat.year, w.monat.month, 15)
            punkte.append({
                "datum": m15.isoformat(), "median": round(w.erwartet, 1), "sicherheit": 1.0,
                "ki80_lo": round(w.lo80, 1), "ki80_hi": round(w.hi80, 1), "ki95_lo": round(w.lo95, 1),
                "ki95_hi": round(w.hi95, 1), "roh_hi_80": round(w.hi80, 1), "roh_hi_95": round(w.hi95, 1),
                "gesichert": None if w.gesichert is None else round(w.gesichert, 1),
                "mieter": sum(e.anzahl for e in ds.aktive("Mieter", s, m15)),
                "gaeste": sum(e.anzahl for e in ds.aktive("Gäste", s, m15)),
                "ist_wert": ist,
            })
        prognosen[s] = punkte
        m = ds.prognose.modelle.get(s) if ds.prognose else None
        if m:
            rueck = [{"jahr": mon.year, "monat": mon.month, "ist": round(i, 1), "modell": round(p, 1),
                      "differenz": round(abs(i - p), 1)} for mon, i, p in m.rueckblick]
            modellinfo[s] = {
                "name": m.name, "aic": None, "rmse": None if m.mae is None else round(m.mae, 2),
                "parameter": m.beschreibung, "anzahl_monate_historie": m.monate_historie or None,
                "alternativen": [{"name": n, "aic": None, "rmse": round(f, 2)} for n, f in m.kandidaten if n != m.name],
                "rueckblick": rueck,
                "mittlere_abweichung_rueckblick": round(float(np.mean([r["differenz"] for r in rueck])), 1) if rueck else None,
                "treffer_80": None if m.abdeckung80 is None else round(m.abdeckung80, 3),
            }

    kap = {s: {"brutto": ds.kapazitaet(s, True), "netto": ds.kapazitaet(s)} for s in STANDORTE}
    kap[GESAMT] = {"brutto": ds.kapazitaet(GESAMT, True), "netto": ds.kapazitaet(GESAMT)}
    standorte = {s: _iso_werte(ds.reha(s)) for s in STANDORTE + [GESAMT]}
    return {
        "meta": {"exportiert_am": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "version": __version__,
                 "pivot_aktuell": ds.pivot_aktualisiert is not False, "ist_bis": ds.stichtag.isoformat()},
        "standorte": standorte,
        "haeuser": {h: {"standort": s, "werte": _iso_werte(ds.pivot.haeuser[h])} for h, s in ds.pivot.haus_standort.items()},
        "mieter": liste("Mieter"),
        "gaeste": liste("Gäste"),
        "anreisen": liste("Anreise"),
        "prognosen": prognosen,
        "modellinfo": modellinfo,
        "hybrid": {"fenster_tage": 30, "bias": {}, "validiert_am": "", "mae_je_standort": {}, "rmse_je_standort": {}},
        "saisonprofile": _saisonprofile(ds),
        "niveauoffsets": {s: 0.0 for s in STANDORTE},
        "kalender": {"feiertage": [], "ferien": []},
        "massnahmen": {},
        "externe_belegungen": belegungsliste(("DRK", "Landkreis", "UWT", "Pflegeschule")),
        "interne_belegungen": belegungsliste(("FRAI", "Jugendhilfe")),
        "kapazitaeten": kap,
        "kapazitaeten_haeuser": {},
    }


def html_aktualisieren(html_pfad: Path, daten: dict) -> int:
    """Ersetzt nur den Inhalt des Datenblocks; legt vorher eine .bak-Sicherung an."""
    with open(html_pfad, encoding="utf-8", newline="") as f:  # Zeilenenden unverändert lassen
        inhalt = f.read()
    start = inhalt.find(JSON_OEFFNEN)
    if start == -1:
        raise ValueError(f"Datenblock {JSON_OEFFNEN} nicht in {html_pfad.name} gefunden – nichts geändert.")
    start += len(JSON_OEFFNEN)
    ende = inhalt.find(JSON_SCHLIESSEN, start)
    if ende == -1:
        raise ValueError("Schließendes </script> des Datenblocks fehlt – nichts geändert.")
    neu = json.dumps(daten, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for ziel, text in ((html_pfad.with_suffix(html_pfad.suffix + ".bak"), inhalt),
                       (html_pfad, inhalt[:start] + neu + inhalt[ende:])):
        with open(ziel, "w", encoding="utf-8", newline="") as f:
            f.write(text)
    return len(neu)
