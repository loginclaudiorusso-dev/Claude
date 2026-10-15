"""Suche nach Namen oder Zimmernummer über alle Quellen: Anreiselisten, UWT-Listen, Gebäudeplan,
Zimmerplan-Zuteilungen und Zimmer-Pivot.

* Name („Meier“, „Anna Kolmer“): je Person/Aufenthalt Zimmer, Zeitraum, Gruppe, Quelle und Notiz.
* Zimmer („322“, „2-322“, „3.1-E01“, „E01“): alle Zimmer mit der Nummer in allen Häusern – mit
  aktueller und kommender Belegung, leere Zimmer als „frei“.

Rein, ohne Qt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from . import anreiseliste
from . import zimmerplan as zp


@dataclass
class Treffer:
    name: str
    massnahme: str
    gruppe: str
    von: date
    bis: date | None
    zimmer_id: str = ""          # leer = noch kein Zimmer
    quelle: str = ""             # Anreiseliste | UWT | Gebäudeplan
    notiz: str = ""
    person: str = ""             # Schlüssel der Anreise-Person (zum Öffnen)
    frei: bool = False           # Zimmersuche: Zimmer ist (ab heute) leer bzw. hat freie Betten
    gesperrt: bool = False

    @property
    def zimmer_text(self) -> str:
        if not self.zimmer_id:
            return "noch kein Zimmer"
        return self.zimmer_id.removeprefix("GS-")

    def status(self, heute: date) -> str:
        if self.gesperrt:
            return f"gesperrt bis {self.bis:%d.%m.%Y}" if self.bis else "gesperrt"
        if self.frei:
            return "frei" if self.bis is None else f"frei bis {self.bis:%d.%m.%Y}"
        if self.von > heute:
            return f"kommt in {(self.von - heute).days} Tagen" if (self.von - heute).days > 1 else "kommt morgen"
        if self.bis is not None and self.bis < heute:
            return "abgereist"
        return "im Haus"


def _woerter(text: str) -> list[str]:
    return [w for w in re.split(r"[\s,;]+", text.lower()) if w]


def passt(name: str, suche: str) -> bool:
    """Alle Suchwörter kommen im Namen vor – Reihenfolge egal („anna kolmer“ findet „Kolmer, Anna“)."""
    name = name.lower()
    return all(w in name for w in _woerter(suche))


_ZIMMER = re.compile(r"^\s*(?:gs-)?(?:([\d.]+)\s*-\s*)?([a-z]?\d{2,3})\s*$", re.I)


def ist_zimmersuche(suche: str) -> bool:
    return bool(_ZIMMER.match(suche))


def zimmer_suchen(suche: str, stand: zp.Planstand, heute: date) -> list[Treffer]:
    """Alle Zimmer mit der Nummer (optional mit Haus) – Belegungen ab heute, sonst „frei“."""
    m = _ZIMMER.match(suche)
    haus, nr = (m.group(1) or ""), m.group(2).upper()
    ergebnis = []
    for z in stand.zimmer:
        if z.nr.upper() != nr or (haus and z.haus != haus):
            continue
        aktuell = sorted((b for b in stand.lage.belegungen.get(z.id, [])
                          if b.art in ("belegt", "geplant") and b.bis >= heute), key=lambda b: b.von)
        gesperrt = [b for b in stand.lage.belegungen.get(z.id, []) if b.art == "gesperrt" and b.von <= heute <= b.bis]
        for b in gesperrt:
            ergebnis.append(Treffer(f"gesperrt · {b.grund}" if b.grund else "gesperrt", "", "", b.von, b.bis, z.id,
                                    "Gebäudeplan", gesperrt=True))
        for b in aktuell:
            quelle = ("Zimmer-Pivot" if b.name == zp.PIVOT_NAME else "Zimmerplan (geplant)" if b.art == "geplant"
                      else "Gebäudeplan")
            ergebnis.append(Treffer(b.name, b.massnahme, zp.belegung_gruppe(b) or "", b.von, b.bis, z.id, quelle,
                                    person=b.person if b.art == "geplant" else ""))
        da = sum(1 for b in aktuell if b.von <= heute)
        if da < z.betten and not gesperrt:
            frei_bis = min((b.von for b in aktuell if b.von > heute), default=None)
            text = (f"– frei – ({z.betten} {'Bett' if z.betten == 1 else 'Betten'})" if da == 0
                    else f"– {z.betten - da} von {z.betten} Betten frei –")
            ergebnis.append(Treffer(text, "", "", heute, frei_bis - timedelta(days=1) if frei_bis else None, z.id,
                                    "Zimmer", frei=True))
    return sorted(ergebnis, key=lambda t: (zp._haus_sort(t.zimmer_id.split("-")[1]), not t.frei, t.von))


def suchen(suche: str, stand: zp.Planstand, personen: list[anreiseliste.Person] | None = None,
           heute: date | None = None) -> list[Treffer]:
    heute = heute or date.today()
    if len(suche.strip()) < 2:
        return []
    if ist_zimmersuche(suche):
        return zimmer_suchen(suche, stand, heute)
    if personen is None:
        personen, _ = anreiseliste.laden()
    ergebnis: list[Treffer] = []
    gesehen: set[tuple[str, str]] = set()      # (Name, Zimmer) – Gebäudeplan-Doppel vermeiden

    # 1) Anreisen mit Internat und UWT (mit Zimmer, falls zugeteilt)
    for b in stand.bedarf:
        if " – Platz " in b.name or not passt(b.name, suche):
            continue
        zuw = stand.zugewiesen(b.schluessel)
        zid = zuw["zimmer"] if zuw else ""
        p = next((p for p in personen if p.schluessel == b.schluessel), None)
        ergebnis.append(Treffer(b.name, b.massnahme, b.gruppe, b.von, b.bis, zid,
                                "UWT" if b.gruppe == "UWT" else "Anreiseliste", b.bemerkung, p.schluessel if p else ""))
        gesehen.add((b.name.lower(), zid))
    # 2) Anreisen ohne Internat (stehen nicht im Zimmerplan)
    for p in personen:
        if not p.internat and passt(p.name, suche):
            ergebnis.append(Treffer(p.name, p.massnahme, p.gruppe, p.anreise, p.abreise, "", "Anreiseliste (ohne Internat)",
                                    p.bemerkung, p.schluessel))
    # 3) Gebäudeplan: wer schon im Belegungssystem gebucht ist
    for zid, bs in stand.lage.belegungen.items():
        for b in bs:
            if b.art != "belegt" or b.name == zp.PIVOT_NAME or not passt(b.name, suche):
                continue
            if (b.name.lower(), zid) in gesehen:
                continue
            gesehen.add((b.name.lower(), zid))
            ergebnis.append(Treffer(b.name, b.massnahme, zp.belegung_gruppe(b) or "", b.von, b.bis, zid, "Gebäudeplan"))
    # im Haus / kommt zuerst, dann nach Anreise; Abgereiste ans Ende
    return sorted(ergebnis, key=lambda t: (t.status(heute) == "abgereist", t.von, t.name.lower()))
