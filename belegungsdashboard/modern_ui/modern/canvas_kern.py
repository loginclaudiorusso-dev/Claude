"""AI-Canvas: eine Eingabe in normalen Worten („freie Zimmer Haus 2“, „ohne Zimmer“, „neu“, „EMR morgen“,
„Mängel unbewohnbar“, „Abreisen diese Woche“, „Müller“) → verstandene Filter und Antwort-Karten (Kennzahlen, Personen,
Zimmer, Abreisen, Seiten). Rein aus den Daten, ohne KI und ohne NiceGUI – schnell genug für Live-Filterung."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from belegung import zimmerplan as zp

from . import anreisen_kern as ank
from . import zimmer_kern as zk
from .kern import kurz

HAEUSER = {"2", "3.1", "3.2", "3.3", "6"}
STATUS = {"frei": "frei", "freie": "frei", "freien": "frei", "verfügbar": "frei", "verfuegbar": "frei", "leer": "frei",
          "belegt": "belegt", "belegte": "belegt", "geplant": "geplant", "geplante": "geplant", "gesperrt": "gesperrt"}
MAENGEL = {"mängel", "maengel", "mangel", "defekt", "defekte", "kaputt", "schaden"}
MERKMALE = {"tier": "tiere", "tiere": "tiere", "hund": "tiere", "katze": "tiere", "doppel": "doppel", "doppelzimmer": "doppel",
            "vinyl": "Vinyl", "teppich": "Teppich", "renoviert": "reno", "renovierte": "reno"}
GRUPPEN = {"emr": "EMR", "ass": "ASS", "assessment": "ASS", "rvl": "RVL", "rvt": "RVT", "reha": "Reha", "uwt": "UWT",
           "gast": "Gast", "gäste": "Gast", "gaeste": "Gast", "mieter": "Mieter"}
LEER = {"zeige", "zeig", "mir", "alle", "die", "der", "das", "den", "im", "in", "am", "an", "für", "fuer", "von", "und", "mit",
        "welche", "wer", "wo", "was", "wie", "viele", "gibt", "es", "ist", "sind", "noch", "haben", "hat", "bitte", "liste",
        "zimmer", "personen", "person", "leute", "anreise", "anreisen", "kommt", "kommen", "ab", "bis"}


@dataclass
class Verstanden:
    haus: str = ""
    status: str = ""
    maengel: bool = False
    unbewohnbar: bool = False
    merkmale: set = field(default_factory=set)
    gruppen: set = field(default_factory=set)
    neu: bool = False
    ohne: bool = False
    mit: bool = False
    abreisen: bool = False
    anreisen: bool = False
    von: date | None = None
    bis: date | None = None
    zeit: str = ""
    rest: str = ""               # übrige Wörter: Name, Zimmernummer, Maßnahme …

    @property
    def zimmerfrage(self) -> bool:
        return bool(self.haus or self.status or self.maengel or self.unbewohnbar or self.merkmale
                    or (self.rest and _zimmernummer(self.rest)))

    @property
    def personenfrage(self) -> bool:
        return bool(self.neu or self.ohne or self.mit or self.gruppen or self.anreisen
                    or (self.von and not self.abreisen and not self.zimmerfrage)
                    or (self.rest and not _zimmernummer(self.rest)))

    def tags(self) -> list[str]:
        t = []
        if self.status:
            t.append({"frei": "freie Zimmer", "belegt": "belegte Zimmer", "geplant": "geplante Zimmer",
                      "gesperrt": "gesperrte Zimmer"}[self.status])
        if self.haus:
            t.append(f"Haus {self.haus}")
        if self.unbewohnbar:
            t.append("unbewohnbar")
        elif self.maengel:
            t.append("mit Mängeln")
        t += [{"tiere": "Tier", "doppel": "Doppelzimmer", "Vinyl": "Vinyl", "Teppich": "Teppich", "reno": "renoviert"}[m]
              for m in sorted(self.merkmale)]
        t += [zp.GRUPPE_LABEL.get(g, g) for g in sorted(self.gruppen)]
        if self.neu:
            t.append("neu (7 Tage)")
        if self.ohne:
            t.append("ohne Zimmer")
        if self.mit:
            t.append("mit Zimmer")
        if self.abreisen:
            t.append("Abreisen")
        if self.zeit:
            t.append(self.zeit)
        if self.rest:
            t.append(f"„{self.rest}“")
        return t


def _zimmernummer(text: str) -> bool:
    return bool(re.fullmatch(r"(\d(\.\d)?-)?[a-zA-Z]?\d{2,3}", text.strip()))


def verstehen(text: str, heute: date) -> Verstanden:
    v = Verstanden()
    text = re.sub(r"(\d),(\d)", r"\1.\2", text)          # „Haus 3,1“ → 3.1
    t = " " + text.lower().replace(",", " ").replace("?", " ").replace("!", " ") + " "
    m = re.search(r"\bhaus\s*(\d(?:[.,]\d)?)\b|\bh\s?(\d\.\d|\d)\b", text.lower())
    if m:
        h = (m.group(1) or m.group(2)).replace(",", ".")
        if h in HAEUSER:
            v.haus = h
            t = t.replace(m.group(0), " ")
    for wort, text_ in (("übermorgen", "übermorgen"), ("uebermorgen", "übermorgen"), ("morgen", "morgen"), ("heute", "heute")):
        if f" {wort} " in t:
            d = heute + timedelta(days={"heute": 0, "morgen": 1, "übermorgen": 2}[text_])
            v.von = v.bis = d
            v.zeit = text_
            t = t.replace(f" {wort} ", " ")
            break
    if re.search(r"\bnächste[nr]?\s+woche\b|\bnaechste[nr]?\s+woche\b", t):
        mo = heute - timedelta(days=heute.weekday()) + timedelta(weeks=1)
        v.von, v.bis, v.zeit = mo, mo + timedelta(days=6), "nächste Woche"
        t = re.sub(r"\bn(ä|ae)chste[nr]?\s+woche\b", " ", t)
    elif re.search(r"\b(diese|der)\s+woche\b|\bwoche\b", t):
        v.von, v.bis, v.zeit = heute, heute - timedelta(days=heute.weekday()) + timedelta(days=6), "diese Woche"
        t = re.sub(r"\b(diese|der)\s+woche\b|\bwoche\b", " ", t)
    elif re.search(r"\bmonat\b", t):
        v.von, v.bis, v.zeit = heute, heute + timedelta(days=30), "nächste 30 Tage"
        t = re.sub(r"\b(diese[nr]?|nächste[nr]?|im)?\s*monat\b", " ", t)
    if re.search(r"\bohne\s+zimmer\b|\bohne\b|\bkein(e|en)?\s+zimmer\b", t):
        v.ohne = True
        t = re.sub(r"\bohne\s+zimmer\b|\bohne\b|\bkein(e|en)?\s+zimmer\b", " ", t)
    if re.search(r"\bmit\s+zimmer\b", t):
        v.mit = True
        t = re.sub(r"\bmit\s+zimmer\b", " ", t)
    if re.search(r"\bbad\s+(über|ueber)\s+(den\s+)?flur\b|\bmänner\b", t):
        v.merkmale.add("maenner")
        t = re.sub(r"\bbad\s+(über|ueber)\s+(den\s+)?flur\b|\bmänner\b", " ", t)
    rest = []
    for w in t.split():
        if w in STATUS:
            v.status = STATUS[w]
        elif w in MAENGEL:
            v.maengel = True
        elif w.startswith("unbewohn"):
            v.unbewohnbar = True
        elif w in MERKMALE:
            v.merkmale.add(MERKMALE[w])
        elif w in GRUPPEN:
            v.gruppen.add(GRUPPEN[w])
        elif w in ("neu", "neue", "neuen", "neues"):
            v.neu = True
        elif w.startswith("abreise") or w in ("auszug", "auszüge", "gehen", "reisen"):
            v.abreisen = True
        elif w in ("anreise", "anreisen", "kommt", "kommen", "ankunft"):
            v.anreisen = True
        elif w not in LEER and len(w) > 1:
            rest.append(w)
    v.rest = " ".join(rest)
    return v


# ---------------------------------------------------------------------------------------
# Antwort
# ---------------------------------------------------------------------------------------

@dataclass
class Zahl:
    titel: str
    wert: int
    unter: str
    stufe: str            # ok | warn | krit | blau | akzent | neutral
    ziel: tuple           # (Seite, Zustand-Dict)


@dataclass
class PKarte:
    schluessel: str
    name: str
    zweite: str
    zimmer: str
    zimmer_id: str
    neu_seit: date | None
    kennung: str


@dataclass
class ZKarte:
    zimmer: str
    kurz: str
    status: str
    heute: str
    lage: str
    maengel: str
    stufe: int


@dataclass
class Antwort:
    verstanden: list[str]
    zahlen: list[Zahl] = field(default_factory=list)
    personen: list[PKarte] = field(default_factory=list)
    personen_gesamt: int = 0
    zimmer: list[ZKarte] = field(default_factory=list)
    zimmer_gesamt: int = 0
    abreisen: list = field(default_factory=list)
    seiten: list[tuple[str, str]] = field(default_factory=list)
    alle_personen: tuple | None = None
    alle_zimmer: tuple | None = None


GRENZE = 24


def antwort(stand: zp.Planstand, text: str, heute: date, neu: dict | None = None) -> Antwort:
    from .register import NAV

    neu = neu or {}
    v = verstehen(text, heute)
    a = Antwort(v.tags())
    q = text.strip().lower()
    nur_wort = v.rest and v.tags() == [f"„{v.rest}“"]
    a.seiten = [(t, k) for k, t, _i, _g in NAV if nur_wort and len(q) >= 3 and q in t.lower()]

    # Zimmer
    if v.zimmerfrage:
        schnell = {m for m in v.merkmale if m in ("tiere", "doppel", "maenner", "reno", "Vinyl", "Teppich")}
        if v.maengel:
            schnell.add("maengel")
        mehr = {"maengel": ["stufe:3"]} if v.unbewohnbar else {}
        if v.gruppen:
            mehr["gruppen"], mehr["modus"] = sorted(v.gruppen), "darf"
        f = zk.filter_bauen(v.haus, v.status, schnell, v.rest if _zimmernummer(v.rest) else "", mehr)
        zs = zk.liste(stand, f, v.von or heute)
        a.zimmer_gesamt = len(zs)
        a.zimmer = [ZKarte(z.zimmer, z.kurz, z.status, z.heute, z.lage, z.maengel, z.stufe) for z in zs[:GRENZE]]
        frei = sum(1 for z in zs if z.status in ("frei", "teilweise"))
        a.zahlen.append(Zahl("Zimmer gefunden", len(zs), " · ".join(x for x in (f"Haus {v.haus}" if v.haus else "alle Häuser",
                                                                                  f"am {(v.von or heute):%d.%m.}") if x),
                             "neutral", ("zimmer", {"ansicht": "liste"})))
        if v.status != "frei":
            a.zahlen.append(Zahl("davon frei", frei, "ganz oder 1 Bett", "ok", ("zimmer", {"ansicht": "liste"})))
        a.alle_zimmer = ("zimmer", {"ansicht": "liste", "zl_haus": v.haus, "zl_status": v.status, "zl_schnell": schnell,
                                    "zl_text": v.rest if _zimmernummer(v.rest) else "", "zl_mehr": mehr, "zu_tag": v.von or heute})

    # Abreisen
    if v.abreisen:
        von, bis = v.von or heute, v.bis or (heute + timedelta(days=7))
        a.abreisen = ank.abreisen(stand, von, bis)[:GRENZE]
        a.zahlen.append(Zahl("Abreisen", len(ank.abreisen(stand, von, bis)), f"{von:%d.%m.} – {bis:%d.%m.}", "blau",
                             ("anreisen", {"ansicht": "abreisen"})))

    # Personen (ein Seitenname allein ist keine Personensuche)
    if v.personenfrage and not (nur_wort and a.seiten):
        ps = ank.personen_liste(stand, heute, neu)
        rest = v.rest.lower() if v.rest and not _zimmernummer(v.rest) else ""

        def passt(p) -> bool:
            if v.neu and p.neu_seit is None:
                return False
            if v.ohne and p.zimmer:
                return False
            if v.mit and not p.zimmer:
                return False
            if v.gruppen and not any(g.lower() in p.gruppe.lower() or p.gruppe.lower().startswith(g.lower()) for g in v.gruppen):
                return False
            if v.von and not (v.von <= p.anreise <= (v.bis or v.von)):
                return False
            return not rest or all(w in f"{p.name} {p.gruppe} {p.zimmer}".lower() for w in rest.split())
        treffer = [p for p in ps if passt(p)]
        karten = [PKarte(p.schluessel, p.name, f"{p.gruppe} · {p.zeitraum}", p.zimmer, "", p.neu_seit, p.kennung)
                  for p in treffer]
        if rest and not (v.neu or v.ohne or v.mit or v.gruppen or v.von):     # Name: auch wer schon im Haus wohnt
            from belegung import suche

            bekannt = {k.name for k in karten}
            for t in suche.suchen(v.rest, stand, heute=heute)[:40]:
                if t.name in bekannt:
                    continue
                zeit = f"{t.von:%d.%m.}–{t.bis:%d.%m.%y}" if t.bis else f"ab {t.von:%d.%m.%y}"
                karten.append(PKarte(t.person or "", t.name, " · ".join(x for x in (t.massnahme, zeit) if x),
                                     kurz(t.zimmer_id) if t.zimmer_id else "", t.zimmer_id, None, t.von.isoformat()))
        a.personen_gesamt = len(karten)
        a.personen = karten[:GRENZE]
        ohne = sum(1 for k in karten if not k.zimmer)
        a.zahlen.append(Zahl("Personen gefunden", len(karten), v.zeit or "kommende Anreisen", "neutral",
                             ("anreisen", {"ansicht": "personen"})))
        if not v.ohne and not v.mit:
            a.zahlen.append(Zahl("davon ohne Zimmer", ohne, "noch zuteilen", "krit" if ohne else "ok",
                                 ("anreisen", {"ansicht": "personen", "ps_filter": "ohne"})))
        a.alle_personen = ("anreisen", {"ansicht": "personen", "ps_filter": "neu" if v.neu else "ohne" if v.ohne
                                        else "mit" if v.mit else "alle", "ps_text": rest})

    # Nichts Bestimmtes erkannt → Überblick
    if not a.zahlen:
        n = zk.zaehler(stand, "", heute)
        ps = ank.personen_liste(stand, heute, neu)
        a.zahlen = [Zahl("frei heute", n["frei"], "Zimmer (ganz oder 1 Bett)", "ok", ("zimmer", {"ansicht": "uebersicht", "zu_filter": "frei"})),
                    Zahl("belegt", n["belegt"], "Zimmer heute", "blau", ("zimmer", {"ansicht": "uebersicht", "zu_filter": "belegt"})),
                    Zahl("ohne Zimmer", sum(1 for p in ps if not p.zimmer), "kommende Anreisen", "krit",
                         ("anreisen", {"ansicht": "personen", "ps_filter": "ohne"})),
                    Zahl("neu (7 Tage)", sum(1 for p in ps if p.neu_seit), "erstmals in den Listen", "blau",
                         ("anreisen", {"ansicht": "personen", "ps_filter": "neu"}))]
    return a


VORSCHLAEGE = ["freie Zimmer heute", "ohne Zimmer", "neu", "Mängel Haus 2", "unbewohnbar", "Abreisen diese Woche",
               "EMR nächste Woche", "freie Doppelzimmer"]
