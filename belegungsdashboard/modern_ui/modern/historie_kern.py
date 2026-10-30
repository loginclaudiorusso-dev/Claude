"""Zimmerhistorie: wer wann in welchem Zimmer gewohnt hat – auch nachdem er aus Gebäudeplan und Listen verschwunden ist.

Der Gebäudeplan zeigt immer nur den aktuellen Stand; mit jedem neuen Plan fallen ehemalige Bewohner heraus. Deshalb
merkt sich die neue Oberfläche bei jedem Laden jede Belegung (``importe/modern_zimmerhistorie.json``, mit gesichert):

* **belegt** (laut Gebäudeplan) – Schlüssel Zimmer + Name + Einzug; das späteste gesehene Ende zählt.
* **geplant** (eigene Planung) – Schlüssel Person + Anreise: wird die Person umgeplant, gilt das neue Zimmer, solange
  der Aufenthalt noch nicht begonnen hat (so bleibt keine verworfene Planung hängen).

Beim ersten Mal wird aus den automatischen Sicherungen nachgetragen (Gebäudeplan-Stände der letzten Wochen). Einträge,
die länger als ``AUFBEWAHREN_JAHRE`` vorbei sind, werden gelöscht (Datensparsamkeit). Rein, ohne NiceGUI.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, timedelta

from belegung import speicher
from belegung import zimmerplan as zp

log = logging.getLogger(__name__)

DATEI = f"{speicher.IMPORT_ORDNER}/modern_zimmerhistorie.json"
AUFBEWAHREN_JAHRE = 5


@dataclass
class Aufenthalt:
    zimmer: str
    name: str
    von: str              # ISO-Datum
    bis: str
    massnahme: str = ""
    art: str = "belegt"   # belegt (Gebäudeplan) | geplant (eigene Planung)
    person: str = ""      # Schlüssel der Anreise-Person (bei geplant)

    @property
    def schluessel(self) -> str:
        return f"p|{self.person}|{self.von}" if self.art == "geplant" and self.person else f"b|{self.zimmer}|{self.name}|{self.von}"

    @property
    def kurz(self) -> str:
        return self.zimmer.removeprefix("GS-")

    @property
    def zeitraum(self) -> str:
        v, b = date.fromisoformat(self.von), date.fromisoformat(self.bis)
        return f"{v:%d.%m.%Y} – {b:%d.%m.%Y}"


def _laden() -> dict:
    roh = speicher.lesen(DATEI, {})
    return {"eintraege": roh.get("eintraege", []), "nachgetragen": roh.get("nachgetragen", False)}


def alle() -> list[Aufenthalt]:
    felder = Aufenthalt.__dataclass_fields__
    return [Aufenthalt(**{k: v for k, v in e.items() if k in felder}) for e in _laden()["eintraege"]]


def _aus_belegung(b) -> Aufenthalt | None:
    if b.art not in ("belegt", "geplant") or not b.name or b.name == zp.PIVOT_NAME or zp.name_fehlt(b.name):
        return None
    return Aufenthalt(b.zimmer, b.name, b.von.isoformat(), b.bis.isoformat(), b.massnahme or "",
                      "geplant" if b.art == "geplant" else "belegt", b.person or "")


def _zusammenfuehren(bisher: dict[str, Aufenthalt], neu: list[Aufenthalt], heute: date, nur_neue: bool = False) -> bool:
    """Neue Aufenthalte aufnehmen; bei bekannten gilt der aktuelle Stand (auch ein früheres Ende nach Abbruch).
    ``nur_neue``: Nachtragen aus alten Sicherungen – bekannte Einträge nie mit einem älteren Stand überschreiben."""
    geaendert = False
    for a in neu:
        alt = bisher.get(a.schluessel)
        if alt is None:
            bisher[a.schluessel] = a
            geaendert = True
            continue
        if nur_neue:
            continue
        if a.art == "geplant" and alt.zimmer != a.zimmer and date.fromisoformat(a.von) > heute:
            bisher[a.schluessel] = a                     # vor dem Einzug umgeplant: das neue Zimmer zählt
            geaendert = True
        elif a.bis != alt.bis or (a.massnahme and a.massnahme != alt.massnahme):
            bisher[a.schluessel] = Aufenthalt(alt.zimmer, alt.name, alt.von, a.bis, a.massnahme or alt.massnahme,
                                              alt.art, alt.person)
            geaendert = True
    return geaendert


def _aufraeumen(bisher: dict[str, Aufenthalt], heute: date) -> bool:
    grenze = (heute - timedelta(days=365 * AUFBEWAHREN_JAHRE)).isoformat()
    weg = [k for k, a in bisher.items() if a.bis < grenze]
    for k in weg:
        del bisher[k]
    return bool(weg)


def _schreiben(bisher: dict[str, Aufenthalt], nachgetragen: bool) -> None:
    eintraege = sorted((asdict(a) for a in bisher.values()), key=lambda e: (e["zimmer"], e["von"], e["name"]))
    speicher.schreiben(DATEI, {"eintraege": eintraege, "nachgetragen": nachgetragen})


def erfassen(stand, heute: date | None = None) -> int:
    """Belegungen des aktuellen Stands in die Historie übernehmen (bei jedem Laden). Gibt die Zahl der Einträge zurück;
    geschrieben wird nur, wenn sich etwas geändert hat."""
    heute = heute or date.today()
    roh = _laden()
    bisher = {a.schluessel: a for a in alle()}
    neu = [a for bs in stand.lage.belegungen.values() for b in bs if (a := _aus_belegung(b))]
    geaendert = _zusammenfuehren(bisher, neu, heute)
    jetzt_geplant = {a.schluessel for a in neu if a.art == "geplant"}
    for k in [k for k, a in bisher.items() if a.art == "geplant" and a.von > heute.isoformat() and k not in jetzt_geplant]:
        del bisher[k]                                   # vor der Anreise gestrichen: war nie ein Aufenthalt
        geaendert = True
    nachgetragen = roh["nachgetragen"]
    if not nachgetragen:
        geaendert |= _zusammenfuehren(bisher, _aus_sicherungen(), heute, nur_neue=True)
        nachgetragen = geaendert = True
    geaendert |= _aufraeumen(bisher, heute)
    if geaendert:
        _schreiben(bisher, nachgetragen)
    return len(bisher)


def _aus_sicherungen() -> list[Aufenthalt]:
    """Gebäudeplan-Stände aus den automatischen Sicherungen (einmalig nachtragen)."""
    from belegung import datensicherung, gebaeudeplan

    erg = []
    for s in datensicherung.liste():
        p = s.pfad / gebaeudeplan.DATEI
        try:
            roh = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except (OSError, ValueError):
            continue
        for d in roh.get("belegungen", []):
            try:
                a = _aus_belegung(gebaeudeplan.Belegung.aus_dict(d))
            except (KeyError, TypeError, ValueError):
                continue
            if a is not None and a.art == "belegt":
                erg.append(a)
    return erg


# ---- Abfragen -----------------------------------------------------------------------------------------

def _ohne_doppelte(liste: list[Aufenthalt]) -> list[Aufenthalt]:
    """Wer wie geplant eingezogen ist, steht als „geplant“ und „belegt“ drin – dann zählt der Gebäudeplan."""
    belegt = [a for a in liste if a.art == "belegt"]
    return [a for a in liste if a.art == "belegt" or not any(
        b.zimmer == a.zimmer and b.name == a.name and b.von <= a.bis and a.von <= b.bis for b in belegt)]


def im_zimmer(zid: str, heute: date | None = None) -> list[Aufenthalt]:
    """Frühere (schon beendete) Aufenthalte in einem Zimmer, neueste zuerst."""
    heute = (heute or date.today()).isoformat()
    return sorted(_ohne_doppelte([a for a in alle() if a.zimmer == zid and a.bis < heute]), key=lambda a: a.von, reverse=True)


def suchen(text: str, heute: date | None = None, anzahl: int = 20) -> list[Aufenthalt]:
    """Ehemalige Bewohner nach Namen (Teile, ohne Groß/Klein), neueste zuerst."""
    heute = (heute or date.today()).isoformat()
    teile = [t for t in text.lower().replace(",", " ").split() if t]
    if not teile:
        return []
    treffer = _ohne_doppelte([a for a in alle() if a.bis < heute and all(t in a.name.lower() for t in teile)])
    return sorted(treffer, key=lambda a: a.bis, reverse=True)[:anzahl]
