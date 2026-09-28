"""Abfragefunktionen, die ein Sprachmodell als Werkzeuge aufrufen darf.

Das Modell sieht nie Rohdaten, sondern nur die Ergebnisse dieser Funktionen. Dadurch
stammen alle Zahlen einer KI-Antwort aus denselben Berechnungen wie im Dashboard.
"""

from __future__ import annotations

import json
from datetime import date

from ..datenstand import Datenstand
from ..konfig import GESAMT, STANDORT_LABEL, STANDORTE
from .verstehen import MONATSNAMEN

_STANDORT_ENUM = ["Bad Pyrmont", "Goslar", "Weser-Ems", "Gesamt"]
_LABEL_ZU_SCHLUESSEL = {v: k for k, v in STANDORT_LABEL.items()}


def _standort(wert: str | None) -> str:
    return _LABEL_ZU_SCHLUESSEL.get(wert or "Gesamt", GESAMT)


def _datum(wert: str) -> date:
    return date.fromisoformat(wert)


def _r(x: float | None) -> float | None:
    return None if x is None else round(float(x), 1)


DEFINITIONEN = [
    {
        "name": "belegung_abfragen",
        "description": (
            "Belegung (belegte Plätze) eines Standorts für einen Tag oder Zeitraum: Durchschnitt, Minimum, "
            "Maximum mit Datum, Personentage, Kapazität und Auslastung. Tage nach dem Datenstand werden aus der "
            "Prognose gefüllt (Feld anteil_prognose). Für einen einzelnen Tag von = bis setzen."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "standort": {"type": "string", "enum": _STANDORT_ENUM},
                "von": {"type": "string", "description": "ISO-Datum YYYY-MM-DD"},
                "bis": {"type": "string", "description": "ISO-Datum YYYY-MM-DD"},
                "brutto": {"type": "boolean", "description": "true = Brutto-Bezug inkl. FRAI/Jugendhilfe"},
            },
            "required": ["standort", "von", "bis", "brutto"],
            "additionalProperties": False,
        },
    },
    {
        "name": "prognose_abfragen",
        "description": (
            "Monatsprognose (Ø belegte Plätze je Monat) mit 80- und 95-%-Spanne, gesichertem Bestand laut "
            "Planung und Auslastung. Abgeschlossene Monate enthalten den Ist-Wert. Horizont ca. 3 Jahre."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "standort": {"type": "string", "enum": _STANDORT_ENUM},
                "von_monat": {"type": "string", "description": "YYYY-MM"},
                "bis_monat": {"type": "string", "description": "YYYY-MM"},
            },
            "required": ["standort", "von_monat", "bis_monat"],
            "additionalProperties": False,
        },
    },
    {
        "name": "tageswerte_abfragen",
        "description": "Einzelne Tageswerte der Belegung (max. 62 Tage), z. B. für Wochentagsmuster oder Verläufe.",
        "input_schema": {
            "type": "object",
            "properties": {
                "standort": {"type": "string", "enum": _STANDORT_ENUM},
                "von": {"type": "string"},
                "bis": {"type": "string"},
            },
            "required": ["standort", "von", "bis"],
            "additionalProperties": False,
        },
    },
    {
        "name": "listen_abfragen",
        "description": (
            "Einträge aus den Listen: Anreisen (geplante Neuaufnahmen), Mieter, Gäste oder sonstige Verträge "
            "(DRK, Landkreis, UWT, Pflegeschule, FRAI, Jugendhilfe), die im Zeitraum beginnen bzw. aktiv sind."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "kategorie": {"type": "string", "enum": ["Anreise", "Mieter", "Gäste", "DRK", "Landkreis", "UWT",
                                                          "Pflegeschule", "FRAI", "Jugendhilfe"]},
                "standort": {"type": "string", "enum": _STANDORT_ENUM},
                "von": {"type": "string"},
                "bis": {"type": "string"},
            },
            "required": ["kategorie", "standort", "von", "bis"],
            "additionalProperties": False,
        },
    },
    {
        "name": "haeuser_abfragen",
        "description": "Belegung je Haus/Gebäude an einem Tag.",
        "input_schema": {
            "type": "object",
            "properties": {"standort": {"type": "string", "enum": _STANDORT_ENUM}, "tag": {"type": "string"}},
            "required": ["standort", "tag"],
            "additionalProperties": False,
        },
    },
    {
        "name": "stammdaten_abfragen",
        "description": "Kapazitäten je Standort, Datenstand (letzter Tag mit Ist-Werten), Prognosemodelle und deren Backtest-Güte.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


class Werkzeuge:
    def __init__(self, ds: Datenstand):
        self.ds = ds

    def ausfuehren(self, name: str, eingabe: dict) -> str:
        try:
            ergebnis = getattr(self, name)(**eingabe)
        except Exception as exc:  # Fehler an das Modell zurückgeben, nicht abstürzen
            return json.dumps({"fehler": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False)
        return json.dumps(ergebnis, ensure_ascii=False, default=str)

    def belegung_abfragen(self, standort: str, von: str, bis: str, brutto: bool = False) -> dict:
        s, v, b = _standort(standort), _datum(von), _datum(bis)
        v = max(v, self.ds.erster_tag)
        df = self.ds.verlauf(s, v, b, brutto)
        w = df["wert"]
        kap = self.ds.kapazitaet(s, brutto)
        return {
            "standort": STANDORT_LABEL[s], "von": v, "bis": b, "bezug": "brutto" if brutto else "netto",
            "durchschnitt": _r(w.mean()), "maximum": _r(w.max()), "tag_maximum": w.idxmax().date(),
            "minimum": _r(w.min()), "tag_minimum": w.idxmin().date(), "personentage": _r(w.sum()),
            "kapazitaet": kap or None, "auslastung_durchschnitt": _r(w.mean() / kap * 100) if kap else None,
            "anteil_prognose": _r((~df["ist"]).mean() * 100),
            "prognose_80_spanne_durchschnitt": [_r(df["lo80"].mean()), _r(df["hi80"].mean())] if (~df["ist"]).any() else None,
        }

    def prognose_abfragen(self, standort: str, von_monat: str, bis_monat: str) -> dict:
        s = _standort(standort)
        von = date.fromisoformat(von_monat + "-01")
        bis = date.fromisoformat(bis_monat + "-01")
        zeilen = []
        for w in (self.ds.prognose.werte.get(s, []) if self.ds.prognose else []):
            if von <= w.monat <= bis:
                mp = self.ds.monatsprognose(s, w.monat)
                zeilen.append({
                    "monat": f"{MONATSNAMEN[w.monat.month - 1]} {w.monat.year}", "art": w.art,
                    "erwartet": _r(mp["erwartet"]), "spanne_80": [_r(mp["lo80"]), _r(mp["hi80"])],
                    "spanne_95": [_r(mp["lo95"]), _r(mp["hi95"])], "gesichert": _r(mp["gesichert"]),
                    "kapazitaet": mp["kapazitaet"] or None,
                    "auslastung_prozent": _r(mp["anteil"] * 100) if mp["anteil"] else None,
                })
        return {"standort": STANDORT_LABEL[s], "monate": zeilen[:36]}

    def tageswerte_abfragen(self, standort: str, von: str, bis: str) -> dict:
        s, v, b = _standort(standort), _datum(von), _datum(bis)
        v = max(v, self.ds.erster_tag)
        df = self.ds.verlauf(s, v, b).iloc[:62]
        return {"standort": STANDORT_LABEL[s], "tage": [
            {"datum": i.date(), "wochentag": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][i.weekday()],
             "belegt": _r(r.wert), "prognose": not r.ist} for i, r in df.iterrows()]}

    def listen_abfragen(self, kategorie: str, standort: str, von: str, bis: str) -> dict:
        s, v, b = _standort(standort), _datum(von), _datum(bis)
        treffer = [e for e in self.ds.eintraege if e.kategorie == kategorie and s in (GESAMT, e.standort)
                   and (v <= e.von <= b if kategorie == "Anreise" else (e.von <= b and e.bis >= v))]
        return {"kategorie": kategorie, "anzahl_eintraege": len(treffer),
                "summe_personen": sum(e.anzahl for e in treffer),
                "eintraege": [{"von": e.von, "bis": None if e.nur_termin or e.bis.year >= 2099 else e.bis,
                               "standort": STANDORT_LABEL[e.standort], "anzahl": e.anzahl,
                               "bezeichnung": e.bezeichnung} for e in sorted(treffer, key=lambda e: e.von)[:40]]}

    def haeuser_abfragen(self, standort: str, tag: str) -> dict:
        s, t = _standort(standort), _datum(tag)
        return {"tag": t, "haeuser": [{"haus": h, "standort": STANDORT_LABEL[self.ds.pivot.haus_standort[h]],
                                       "belegt": _r(w)} for h, w in self.ds.haeuser_am(s, t)]}

    def stammdaten_abfragen(self) -> dict:
        modelle = {}
        if self.ds.prognose:
            for s, m in self.ds.prognose.modelle.items():
                modelle[STANDORT_LABEL[s]] = {"modell": m.name, "fehler_1_monat": _r(m.mae_1m),
                                              "fehler_bis_12_monate": _r(m.mae),
                                              "treffer_80_prozent_band": _r((m.abdeckung80 or 0) * 100)}
        return {
            "ist_werte_bis": self.ds.stichtag, "daten_ab": self.ds.erster_tag,
            "kapazitaeten": {STANDORT_LABEL[s]: {"netto": self.ds.kapazitaet(s) or None,
                                                  "brutto": self.ds.kapazitaet(s, True) or None}
                             for s in STANDORTE + [GESAMT]},
            "prognosemodelle": modelle,
            "importierte_listen": {k: {"quelle": v.get("quelle"), "importiert_am": v.get("importiert_am"),
                                       "eintraege": v.get("anzahl")} for k, v in self.ds.importe.items()},
        }
