"""Flur-Raster: Wie viele Abreisewellen laufen je Flur und Woche parallel? (Zeitstrahl → „Flure“)

Ziel der Planung: Auf einem Flur sollen möglichst viele Zimmer im selben Reinigungsfenster frei werden – dann gibt es
wenige Reinigungsanlässe und Übergaben. Gezählt wird je Flur und Woche, zu wie vielen **Abreisewellen** die belegten
Zimmer gehören:

* **Auszug** = das Zimmer wird ganz frei (Doppelzimmer: erst wenn beide weg sind; Umzug: das alte Zimmer wird frei).
* **Abreisewelle** = Auszüge, die ins selbe Reinigungsfenster fallen: Wochenende zählt zum Montag, eine Welle umfasst
  höchstens zwei aufeinanderfolgende Werktage ab dem ersten Auszug (Fr + Mo = eine Welle, Di + Fr = zwei).
* **Gewertet** werden nur lange Aufenthalte (Hauptmaßnahmen). Kurze (EMR, ASS, UWT, Gäste, ≤ 8 Wochen) und Mieter
  stehen als eigene Zahl daneben – sie sind planbar bzw. nicht verschiebbar und machen einen Flur nicht „schlechter“.

An- und Abreisedaten werden nie verändert; das Raster zeigt nur. Rein, ohne NiceGUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import zimmerplan as zp

FLUR_NAME = {"West": "West", "Ost": "Ost"}


@dataclass
class Aufenthalt:
    zimmer: str           # Zimmer-ID
    kurz: str             # „2-105“
    name: str
    von: date
    bis: date
    art: str              # lang | kurz | mieter


@dataclass
class Welle:
    nr: int
    von: date             # erster Reinigungstag der Welle
    bis: date             # letzter Reinigungstag der Welle
    zimmer: list[str] = field(default_factory=list)          # Zimmer-IDs, die in dieser Welle frei werden

    @property
    def text(self) -> str:
        wt = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
        t = f"{wt[self.von.weekday()]} {self.von:%d.%m.}"
        return t if self.bis == self.von else f"{t} / {wt[self.bis.weekday()]} {self.bis:%d.%m.}"


@dataclass
class Zelle:
    woche: date           # Montag
    wellen: list[int]     # Nummern der Wellen, zu denen die belegten Zimmer gehören
    belegt: int           # Zimmer mit gewertetem Aufenthalt
    kurz: int             # Zimmer mit kurzem Aufenthalt
    mieter: int

    @property
    def n(self) -> int:
        return len(self.wellen)

    @property
    def stufe(self) -> str:
        return "leer" if not self.n else "ok" if self.n == 1 else "warn" if self.n == 2 else "krit"


@dataclass
class Flur:
    schluessel: str       # „2|1|West“
    haus: str
    text: str             # „1. OG West“
    zimmer: list[str]
    zellen: list[Zelle] = field(default_factory=list)
    wellen: list[Welle] = field(default_factory=list)
    aufenthalte: list[Aufenthalt] = field(default_factory=list)


def reinigungstag(d: date) -> date:
    """Auszug am Wochenende → gereinigt wird am Montag."""
    while not zp.werktag(d):
        d += timedelta(days=1)
    return d


def _werktage_zwischen(a: date, b: date) -> int:
    """Werktage nach ``a`` bis einschließlich ``b`` (Fr → Mo = 1)."""
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        n += zp.werktag(d)
    return n


def wellen_bilden(auszuege: list[tuple[date, str]]) -> list[Welle]:
    """(Auszugstag, Zimmer) → Wellen. Fest verankert am ersten Tag einer Welle (keine Kettenbildung)."""
    erg: list[Welle] = []
    for tag, zid in sorted((reinigungstag(t), z) for t, z in auszuege):
        if erg and _werktage_zwischen(erg[-1].von, tag) <= 1:
            erg[-1].bis = max(erg[-1].bis, tag)
            erg[-1].zimmer.append(zid)
        else:
            erg.append(Welle(len(erg) + 1, tag, tag, [zid]))
    return erg


def _art(b) -> str | None:
    if b.person.startswith("mv:") or zp.gruppe_von(b.massnahme, "Reha") == "Mieter":
        return "mieter"
    lang = zp.langzeit(b)
    return None if lang is None else ("lang" if lang else "kurz")


def _zusammen(intervalle: list[tuple[date, date]]) -> list[tuple[date, date]]:
    """Überlappende bzw. direkt anschließende Aufenthalte eines Zimmers zusammenfassen (Doppelzimmer, Umzug hinein)."""
    erg: list[list[date]] = []
    for von, bis in sorted(intervalle):
        if erg and von <= erg[-1][1] + timedelta(days=1):
            erg[-1][1] = max(erg[-1][1], bis)
        else:
            erg.append([von, bis])
    return [(a, b) for a, b in erg]


def flur_text(z) -> str:
    return f"{zp.etage_text(z.etage)} {FLUR_NAME.get(z.flur, z.flur)}".strip()


def raster(stand: zp.Planstand, start: date, wochen: int = 8) -> list[Flur]:
    """Je Flur (Haus, Etage, West/Ost) die Zellen der ``wochen`` Wochen ab ``start`` (Montag)."""
    start -= timedelta(days=start.weekday())
    ende = start + timedelta(days=7 * wochen - 1)
    flure: dict[tuple, list] = {}
    for z in stand.zimmer:
        if z.aktiv and not z.gaeste:
            flure.setdefault(z.flur_schluessel, []).append(z)
    erg = []
    for (haus, etage, flur), zs in sorted(flure.items(), key=lambda kv: (zp._haus_sort(kv[0][0]), zp._etage_sort(kv[0][1]), kv[0][2])):
        zs.sort(key=lambda z: (z.nummer, z.nr))
        f = Flur(f"{haus}|{etage}|{flur}", haus, flur_text(zs[0]), [z.id for z in zs])
        lang: dict[str, list[tuple[date, date]]] = {}
        for z in zs:
            for b in stand.lage.belegungen.get(z.id, []):
                if b.bis < start - timedelta(days=7) or b.von > ende + timedelta(days=7):
                    continue
                if (art := _art(b)) is None:
                    continue
                name = zp.anzeige_name(b.name) if b.name else (b.massnahme or "")
                f.aufenthalte.append(Aufenthalt(z.id, z.kurz, name, b.von, b.bis, art))
                if art == "lang":
                    lang.setdefault(z.id, []).append((b.von, b.bis))
        bloecke = {zid: _zusammen(iv) for zid, iv in lang.items()}
        f.wellen = wellen_bilden([(bis, zid) for zid, ivs in bloecke.items() for _von, bis in ivs])
        welle_von = {}
        for w in f.wellen:
            for zid in w.zimmer:
                welle_von.setdefault(zid, []).append(w)
        for i in range(wochen):
            mo = start + timedelta(days=7 * i)
            so = mo + timedelta(days=6)
            wellen, belegt = set(), set()
            for zid, ivs in bloecke.items():
                for von, bis in ivs:
                    if von <= so and bis >= mo:
                        belegt.add(zid)
                        rt = reinigungstag(bis)
                        wellen.update(w.nr for w in welle_von[zid] if w.von <= rt <= w.bis)
            def zimmer_mit(art):
                return len({a.zimmer for a in f.aufenthalte if a.art == art and a.von <= so and a.bis >= mo})
            f.zellen.append(Zelle(mo, sorted(wellen), len(belegt), zimmer_mit("kurz"), zimmer_mit("mieter")))
        erg.append(f)
    return erg


def zusammenfassung(flure: list[Flur], woche: int = 0) -> dict[str, int]:
    """Wie viele Flure haben in der Woche ``woche`` (Index) 1, 2 bzw. 3+ Wellen?"""
    erg = {"ok": 0, "warn": 0, "krit": 0, "leer": 0}
    for f in flure:
        if woche < len(f.zellen):
            erg[f.zellen[woche].stufe] += 1
    return erg


def detail(f: Flur, woche: date) -> dict:
    """Für das Panel: Wellen dieser Woche mit Zimmern und Aufenthalten, dazu kurze Aufenthalte und Mieter."""
    so = woche + timedelta(days=6)
    zelle = next(z for z in f.zellen if z.woche == woche)
    aktiv = [a for a in f.aufenthalte if a.von <= so and a.bis >= woche]
    wellen = []
    for w in f.wellen:
        if w.nr in zelle.wellen:
            wellen.append((w, sorted((a for a in aktiv if a.art == "lang" and a.zimmer in w.zimmer
                                      and w.von <= _ende_im_zimmer(f, a) <= w.bis), key=lambda a: (a.kurz, a.von))))
    return {"zelle": zelle, "wellen": wellen,
            "kurz": sorted((a for a in aktiv if a.art == "kurz"), key=lambda a: (a.kurz, a.von)),
            "mieter": sorted((a for a in aktiv if a.art == "mieter"), key=lambda a: (a.kurz, a.von))}


def _ende_im_zimmer(f: Flur, a: Aufenthalt) -> date:
    """Reinigungstag, an dem das Zimmer nach diesem Aufenthalt ganz frei wird (Doppelzimmer: Partner zählt mit)."""
    ivs = _zusammen([(x.von, x.bis) for x in f.aufenthalte if x.zimmer == a.zimmer and x.art == "lang"])
    return next(reinigungstag(bis) for von, bis in ivs if von <= a.von <= bis)
