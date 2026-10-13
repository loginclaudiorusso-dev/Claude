"""Belegung optimieren: bessere Zimmer, Tausche und Regelverstöße – mit Begründung, zum Bestätigen.

Bewertet wird jede Belegung wie beim Zuteilen (``zimmer_wert``: Haus/Etage/Gruppe/Reserven,
``anschluss_wert``: nahtlose Folgebelegung, ``flur_mischung``: lange Aufenthalte auf einen Flur).

* **Umzug** (geplant, noch nicht angereist): ein anderes zulässiges Zimmer ist deutlich besser.
* **Tausch** (zwei geplante Personen, auch aus verschiedenen Gruppen): beide Zimmer passen über Kreuz besser.
* **Anreise zusammen:** Wer mit derselben Anreise (gleicher Tag, gleiche Maßnahme) kommt, soll auf einem Flur
  wohnen – je Person derselben Anreise auf dem Flur gibt es Punkte. So rücken Gruppen mit jeder Optimierung
  weiter zusammen (Personen mit Tier ausgenommen, UWT über „UWT neu zuteilen“).
* **Regelverstoß** (geplant oder im Gebäudeplan): Zimmer verletzt eine feste Regel (z. B. lange Maßnahme
  auf Haus 2, 1. OG, kein UWT im Doppelzimmer) – mit freiem, passendem Ersatz.
* **Im Belegungssystem umbuchen** (Gebäudeplan, noch nicht angereist): deutlich besseres Zimmer frei – das
  Programm bucht nicht selbst um, sondern legt eine Aufgabe an.

Personen mit DZ-Partner laut Liste werden nicht einzeln verschoben. Wer schon im Belegungssystem eingetragen
ist (Aufgaben → Haken), wird nur bei deutlichem Gewinn und nicht vorausgewählt vorgeschlagen.
Rein, ohne Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from . import zimmerplan as zp
from . import zkl

GEWINN_UMZUG = 2.0          # so viele Punkte muss ein anderes Zimmer besser sein
GEWINN_TAUSCH = 2.5
GEWINN_UMBUCHEN = 4.0       # Gebäudeplan-Buchungen: nur bei klarem Vorteil vorschlagen
REGEL_BONUS = 5.0           # eine verletzte Regel aufzulösen zählt so viel wie ein deutlich besseres Zimmer
KOHORTE_PUNKTE = 1.5        # je Person derselben Anreise auf dem Flur (Maßnahme zusammen auf einem Flur) …
KOHORTE_MAX = 6.0           # … höchstens so viel
ARTEN = {"regel": "Regelverstoß", "umzug": "Besseres Zimmer", "tausch": "Tausch", "umbuchen": "Im Belegungssystem umbuchen"}


@dataclass
class Vorschlag:
    art: str
    personen: list[str]                 # Personen-Schlüssel
    namen: list[str]
    von_zimmer: list[str]
    nach_zimmer: list[str]
    zeitraum: str
    gewinn: float
    gruende: list[str] = field(default_factory=list)
    umsetzbar: bool = True              # False: nur Aufgabe (Buchung im Belegungssystem)
    vorauswahl: bool = True
    hinweis: str = ""

    @property
    def text(self) -> str:
        k = lambda z: z.removeprefix("GS-")
        if self.art == "tausch":
            return (f"{self.namen[0]} ({k(self.von_zimmer[0])} → {k(self.nach_zimmer[0])}) ⇄ "
                    f"{self.namen[1]} ({k(self.von_zimmer[1])} → {k(self.nach_zimmer[1])})")
        return f"{self.namen[0]}: {k(self.von_zimmer[0])} → {k(self.nach_zimmer[0])}"


# ---------------------------------------------------------------------------------------
# Bewertung mit Begründung
# ---------------------------------------------------------------------------------------

def _flur_ids(lage: zp.Lage) -> dict[tuple, list[str]]:
    ids: dict[tuple, list[str]] = {}
    for z in lage.zimmer.values():
        if z.aktiv:
            ids.setdefault(z.flur_schluessel, []).append(z.id)
    return ids


class Kohorten:
    """Wer gehört zu welcher Anreise-Gruppe (gleicher Tag, gleiche Maßnahme)? Personen mit Tier, UWT (eigene
    Klassenplanung), Gäste und Mieter zählen nicht – sie wohnen ohnehin woanders."""

    def __init__(self, bedarf: list[zp.Bedarf]):
        self.von_person = {b.schluessel: b.anreise_kennung or f"{b.von.isoformat()}|{b.gruppe}" for b in bedarf
                           if not b.tier and b.gruppe not in ("UWT", "Gast", "Mieter")}
        self._namen = [(zp._namenswoerter(b.name), b) for b in bedarf if b.schluessel in self.von_person]
        self._cache: dict[tuple, str | None] = {}

    def von(self, bel: zp.Belegung) -> str | None:
        if bel.person:
            return self.von_person.get(bel.person)
        if bel.art != "belegt" or not bel.name or bel.name == zp.PIVOT_NAME:
            return None
        key = (bel.name, bel.von)
        if key not in self._cache:          # Gebäudeplan-Eintrag einer Person aus der Anreiseliste
            w, t = zp._namenswoerter(bel.name), timedelta(days=3)
            b = next((b for ws, b in self._namen if ws and ws <= w and b.von <= bel.bis + t and bel.von - t <= b.bis), None)
            self._cache[key] = self.von_person[b.schluessel] if b else None
        return self._cache[key]

    @staticmethod
    def text(kennung: str) -> str:
        tag, _, gruppe = kennung.partition("|")
        try:
            tag = date.fromisoformat(tag).strftime("%d.%m.")
        except ValueError:
            pass
        return f"{zp.GRUPPE_LABEL.get(gruppe, gruppe)} {tag}".strip()

    def auf_flur(self, lage: zp.Lage, ids: list[str], b: zp.Bedarf, ohne: frozenset = frozenset()) -> tuple[int, str | None]:
        """(Anzahl anderer aus derselben Anreise auf diesen Zimmern, Kennung). ``ohne``: nicht mitzählen
        (beim Tausch der Tauschpartner, der den Flur ja verlässt)."""
        k = self.von_person.get(b.schluessel)
        if k is None:
            return 0, None
        n = sum(1 for zid in ids for x in lage.belegungen.get(zid, []) if x.person != b.schluessel and x.person not in ohne
                and x.art in ("belegt", "geplant") and x.bis >= b.von and x.von <= b.bis and self.von(x) == k)
        return n, k


def bewertung(lage: zp.Lage, z: zp.Zimmer, b: zp.Bedarf, flur_ids: dict, kohorten: Kohorten | None = None,
              ohne: frozenset = frozenset()) -> tuple[float, list[tuple[float, str]]]:
    d = list(zp.zimmer_wert_details(z, b))
    if kohorten is not None:
        n, k = kohorten.auf_flur(lage, flur_ids.get(z.flur_schluessel, []), b, ohne)
        if n:
            d.append((min(KOHORTE_PUNKTE * n, KOHORTE_MAX),
                      f"{n} aus derselben Anreise ({Kohorten.text(k)}) auf dem Flur"))
    a = zp.anschluss_wert(lage, z, b)
    if a > 0:
        d.append((a, "nahtlose Folgebelegung – Aus- und Einzugsreinigung fallen zusammen"))
    elif a < 0:
        d.append((a, "kein Reinigungstag zwischen Aus- und Einzug"))
    f = zp.FLUR_GEWICHT * zp.flur_mischung(lage, flur_ids.get(z.flur_schluessel, []), b)
    if abs(f) >= 0.5:
        d.append((f, "Flur passt zur Aufenthaltsdauer (lange zu langen)" if f > 0
                  else "Flur passt nicht zur Aufenthaltsdauer (lange und kurze gemischt)"))
    return sum(p for p, _t in d), d


def _gruende(alt: list[tuple[float, str]], neu: list[tuple[float, str]]) -> list[str]:
    """Was das neue Zimmer besser macht: neue Pluspunkte und weggefallene Minuspunkte, größte zuerst."""
    alt_t, neu_t = {t: p for p, t in alt}, {t: p for p, t in neu}
    teile = [(p, f"+ {t}") for t, p in neu_t.items() if p > 0 and t not in alt_t]
    teile += [(-p, f"entfällt: {t}") for t, p in alt_t.items() if p < 0 and t not in neu_t]
    return [t for _p, t in sorted(teile, reverse=True)[:3]]


def _zeitraum(b: zp.Bedarf) -> str:
    return f"{b.von:%d.%m.}–{b.bis:%d.%m.%Y}"


def _verschieben(lage: zp.Lage, bel: zp.Belegung, nach: str) -> zp.Belegung:
    lage.belegungen[bel.zimmer] = [x for x in lage.belegungen.get(bel.zimmer, []) if x is not bel]
    neu = zp.Belegung(nach, bel.von, bel.bis, bel.art, bel.name, bel.massnahme, bel.grund, bel.person)
    lage.belegungen.setdefault(nach, []).append(neu)
    return neu


def _bedarf_aus_belegung(bel: zp.Belegung) -> zp.Bedarf:
    gruppe = zp.belegung_gruppe(bel) or "Reha"
    return zp.Bedarf(f"gp:{bel.zimmer}:{bel.von.isoformat()}", bel.name, bel.massnahme, gruppe, bel.von, bel.bis,
                     zp.geschlecht_raten(bel.name), True)


# ---------------------------------------------------------------------------------------
# Vorschläge
# ---------------------------------------------------------------------------------------

def vorschlaege(stand: zp.Planstand, heute: date | None = None, tage: int = 180, haken: dict | None = None,
                mit_tausch: bool = True) -> list[Vorschlag]:
    heute = heute or date.today()
    ende = heute + timedelta(days=tage)
    lage = zp.Lage(stand.lage.zimmer, {k: list(v) for k, v in stand.lage.belegungen.items()}, stand.lage.puffer,
                   stand.lage.abgleich, stand.lage.dz)
    flur_ids = _flur_ids(lage)
    zimmer = [z for z in lage.zimmer.values() if z.aktiv]
    nach_person = {b.schluessel: b for b in stand.bedarf}
    haken = haken or {}
    erg: list[Vorschlag] = []
    koh = Kohorten(stand.bedarf)

    def kandidaten(b: zp.Bedarf, ohne: frozenset) -> list[zp.Zimmer]:
        return [z for z in zimmer if (zp.erlaubt(z, b.gruppe) or (b.tier and z.tiere))
                and lage.freie_betten(z.id, b.von, b.bis, ohne) > 0 and zp.passt(lage, z, b, ohne) is None]

    # 1) Geplante, noch nicht angereiste Personen
    beweglich: list[tuple[zp.Belegung, zp.Bedarf]] = []
    for zid, bs in lage.belegungen.items():
        for bel in bs:
            b = nach_person.get(bel.person) if bel.art == "geplant" and not bel.umzug else None
            if b is not None and heute < b.von <= ende and not (b.dz not in ("", "allein")):
                beweglich.append((bel, b))
    bewertet = []
    for bel, b in beweglich:
        p, d = bewertung(lage, lage.zimmer[bel.zimmer], b, flur_ids, koh)
        regel = zp.passt(lage, lage.zimmer[bel.zimmer], b, frozenset({b.schluessel}))
        bewertet.append((regel is None, p, bel, b, d, regel))
    bewertet.sort(key=lambda x: (x[0], x[1]))                 # Regelverstöße und schlechteste zuerst
    for ok, p0, bel, b, d0, regel in bewertet:
        ohne = frozenset({b.schluessel})
        beste = None
        for z in kandidaten(b, ohne):
            if z.id == bel.zimmer:
                continue
            p, d = bewertung(lage, z, b, flur_ids, koh)
            if beste is None or p > beste[0]:
                beste = (p, z, d)
        if beste is None:
            continue
        p1, z1, d1 = beste
        eingetragen = f"{b.schluessel}|{bel.zimmer}|{b.von.isoformat()}" in haken
        schwelle = GEWINN_UMBUCHEN if eingetragen else GEWINN_UMZUG
        if ok and (p1 - p0 < schwelle or b.gruppe == "UWT"):
            continue                    # UWT: Klassen bleiben zusammen (dafür „UWT neu zuteilen“)
        v = Vorschlag("umzug" if ok else "regel", [b.schluessel], [b.name], [bel.zimmer], [z1.id], _zeitraum(b),
                      round(p1 - p0 + (0 if ok else REGEL_BONUS), 1), ([f"Regel: {regel}"] if regel else []) + _gruende(d0, d1),
                      vorauswahl=not eingetragen,
                      hinweis="schon im Belegungssystem eingetragen – dort ebenfalls umbuchen" if eingetragen else "")
        erg.append(v)
        _verschieben(lage, bel, z1.id)                     # Folgevorschläge sehen den Umzug schon

    # 2) Tausch zweier geplanter Personen (gleiche Gruppe, überlappender Zeitraum)
    if mit_tausch:
        schon = {p for v in erg for p in v.personen}
        aktuell = []
        for zid, bs in lage.belegungen.items():
            for bel in bs:
                b = nach_person.get(bel.person) if bel.art == "geplant" and not bel.umzug else None
                if b is not None and heute < b.von <= ende and b.schluessel not in schon and b.dz in ("", "allein"):
                    aktuell.append((bel, b, bewertung(lage, lage.zimmer[zid], b, flur_ids, koh)))
        aktuell.sort(key=lambda x: x[2][0])
        benutzt: set[str] = set()
        for i, (bel1, b1, (p1, d1)) in enumerate(aktuell[:60]):
            if b1.schluessel in benutzt:
                continue
            bester = None
            for bel2, b2, (p2, d2) in aktuell:
                if b2.schluessel in benutzt or b2 is b1 or bel2.zimmer == bel1.zimmer or "UWT" in (b1.gruppe, b2.gruppe):
                    continue            # auch über Gruppen hinweg, wenn beide Zimmer für beide zulässig sind
                if not (b1.von <= b2.bis and b2.von <= b1.bis):
                    continue
                ohne = frozenset({b1.schluessel, b2.schluessel})
                z1, z2 = lage.zimmer[bel1.zimmer], lage.zimmer[bel2.zimmer]
                if zp.passt(lage, z2, b1, ohne) or zp.passt(lage, z1, b2, ohne):
                    continue
                q1, e1 = bewertung(lage, z2, b1, flur_ids, koh, ohne)
                q2, e2 = bewertung(lage, z1, b2, flur_ids, koh, ohne)
                # vorher ebenfalls ohne den Partner zählen – sonst zählt jeder den anderen als „Gruppe auf dem Flur“
                gewinn = q1 + q2 - bewertung(lage, z1, b1, flur_ids, koh, ohne)[0] - bewertung(lage, z2, b2, flur_ids, koh, ohne)[0]
                if gewinn >= GEWINN_TAUSCH and (bester is None or gewinn > bester[0]):
                    bester = (gewinn, bel2, b2, e1, e2, d2)
            if bester is None:
                continue
            gewinn, bel2, b2, e1, e2, d2 = bester
            eingetragen = any(f"{b.schluessel}|{bel.zimmer}|{b.von.isoformat()}" in haken
                              for b, bel in ((b1, bel1), (b2, bel2)))
            erg.append(Vorschlag("tausch", [b1.schluessel, b2.schluessel], [b1.name, b2.name],
                                 [bel1.zimmer, bel2.zimmer], [bel2.zimmer, bel1.zimmer],
                                 f"{_zeitraum(b1)} / {_zeitraum(b2)}", round(gewinn, 1),
                                 (_gruende(d1, e1) + _gruende(d2, e2))[:3], vorauswahl=not eingetragen,
                                 hinweis="schon im Belegungssystem eingetragen – dort ebenfalls umbuchen" if eingetragen else ""))
            benutzt |= {b1.schluessel, b2.schluessel}
            z1, z2 = bel1.zimmer, bel2.zimmer
            _verschieben(lage, bel1, z2)
            _verschieben(lage, bel2, z1)

    # 3) Gebäudeplan: Regelverstöße und klar bessere Zimmer vor der Anreise (nur als Aufgabe)
    for zid, bs in list(lage.belegungen.items()):
        for bel in list(bs):
            if bel.art != "belegt" or not bel.name or bel.name == zp.PIVOT_NAME or bel.bis < heute or bel.von > ende \
                    or bel.umzug:
                continue                               # Umzug ist schon geplant
            b = _bedarf_aus_belegung(bel)
            tier = zkl.hat_tier(lage, bel)          # Tier steht nicht im Gebäudeplan – ZKL fragen
            if tier is None and lage.zimmer.get(zid) is not None and zp.nur_tier(lage.zimmer[zid]):
                tier = True                          # sonst: wer im UG (nur mit Tier) wohnt, hat eins
            b.tier = bool(tier)
            if b.gruppe in ("Mieter", "Gast") or "," not in bel.name:
                continue                               # Mietverträge/Gäste und Sammel-Einträge nicht verschieben
            tmp = zp.Lage(lage.zimmer, {**lage.belegungen, zid: [x for x in bs if x is not bel]}, lage.puffer)
            z0 = lage.zimmer.get(zid)
            if z0 is None or not z0.aktiv:
                continue
            regel = zp.passt(tmp, z0, b)
            angereist = bel.von <= heute
            if regel is None and angereist or angereist and bel.bis <= heute + timedelta(days=30):
                continue                               # wohnt schon dort und zieht ohnehin bald aus
            if regel and ("belegt" in regel or "Doppelzimmer –" in regel or "nur Männer" in regel):
                regel = None       # Mitbewohner/Geschlecht (nur aus dem Vornamen geschätzt) klärt das Belegungssystem
                if angereist:
                    continue
            p0, d0 = bewertung(tmp, z0, b, flur_ids, koh)
            beste = None
            for z in zimmer:
                if z.id == zid or not (zp.erlaubt(z, b.gruppe)) or tmp.freie_betten(z.id, b.von, b.bis) <= 0:
                    continue
                if zp.passt(tmp, z, b) is not None:
                    continue
                p, d = bewertung(tmp, z, b, flur_ids, koh)
                if beste is None or p > beste[0]:
                    beste = (p, z, d)
            if beste is None:
                continue
            p1, z1, d1 = beste
            if regel is None and p1 - p0 < GEWINN_UMBUCHEN:
                continue
            erg.append(Vorschlag("regel" if regel else "umbuchen", [zp.bewohner_aus(stand, bel).schluessel], [bel.name],
                                 [zid], [z1.id], f"{bel.von:%d.%m.}–{bel.bis:%d.%m.%Y}",
                                 round(p1 - p0 + (REGEL_BONUS if regel else 0), 1),
                                 ([f"Regel: {regel}"] if regel else []) + _gruende(d0, d1), umsetzbar=False,
                                 vorauswahl=False,
                                 hinweis=("wohnt schon dort – Umzug nur, wenn es passt" if angereist
                                          else "im Belegungssystem gebucht – dort umbuchen")))
            _verschieben(lage, bel, z1.id)        # nächster Vorschlag sieht das Zimmer als vergeben
    reihenfolge = {"regel": 0, "umzug": 1, "tausch": 2, "umbuchen": 3}
    return sorted(erg, key=lambda v: (reihenfolge[v.art], -v.gewinn))


def umsetzen(stand: zp.Planstand, auswahl: list[Vorschlag], heute: date | None = None) -> tuple[int, int]:
    """Umsetzbare Vorschläge speichern (Änderungsprotokoll: „Optimierung“); für Buchungen im Belegungssystem
    eine Aufgabe (Wiedervorlage heute) anlegen. Gibt (umgesetzt, Aufgaben) zurück."""
    from . import termine

    heute = heute or date.today()
    nach_person = {b.schluessel: b for b in stand.bedarf}
    zuteilungen, aufgaben = [], 0
    for v in auswahl:
        if v.umsetzbar:
            for person, nach in zip(v.personen, v.nach_zimmer):
                b = nach_person.get(person)
                if b is not None and nach in stand.lage.zimmer:
                    zuteilungen.append(zp.Zuteilung(b, stand.lage.zimmer[nach], "Optimierung"))
        else:
            termine.notiz_speichern(termine.Notiz(
                v.personen[0], v.namen[0],
                f"Im Belegungssystem umbuchen: {v.von_zimmer[0].removeprefix('GS-')} → {v.nach_zimmer[0].removeprefix('GS-')}"
                f" ({'; '.join(v.gruende[:2])})", heute, heute))
            aufgaben += 1
    if zuteilungen:
        zp.zuweisungen_speichern(zuteilungen, "Optimierung")
    return len(zuteilungen), aufgaben
