"""1.75: Feiertage und eigene Schließzeiten. Rein bis auf Lesen und Schreiben.

* **Gesetzliche Feiertage** werden berechnet (Ostern nach Gauß) – ohne Zusatzbibliothek, für jedes Jahr. Standard:
  Niedersachsen; das Bundesland ist je Standort wählbar.
* **Eigene Schließzeiten** je Standort (z. B. „Weihnachtsschließung“, Brückentag): Bezeichnung, von, bis.
* Gespeichert je Standort in ``importe/modern_feiertage.json`` (Bundesland und Schließzeiten).
* Wirkung: Cockpit-Hinweis, wenn in den nächsten Tagen jemand an einem Feiertag oder in einer Schließzeit anreist
  oder abreist; der Kalender zeigt Feiertage und Schließzeiten; die Reinigungsvorschau markiert die Tage.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache

DATEI = "importe/modern_feiertage.json"
STANDARD_LAND = "NI"
LAENDER = {"BW": "Baden-Württemberg", "BY": "Bayern", "BE": "Berlin", "BB": "Brandenburg", "HB": "Bremen",
           "HH": "Hamburg", "HE": "Hessen", "MV": "Mecklenburg-Vorpommern", "NI": "Niedersachsen",
           "NW": "Nordrhein-Westfalen", "RP": "Rheinland-Pfalz", "SL": "Saarland", "SN": "Sachsen",
           "ST": "Sachsen-Anhalt", "SH": "Schleswig-Holstein", "TH": "Thüringen"}
VORSCHAU_TAGE = 14


def ostersonntag(jahr: int) -> date:
    """Gaußsche Osterformel (gregorianisch, mit Ausnahmen)."""
    a, b, c = jahr % 19, jahr // 100, jahr % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    lz = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lz) // 451
    monat = (h + lz - 7 * m + 114) // 31
    tag = (h + lz - 7 * m + 114) % 31 + 1
    return date(jahr, monat, tag)


@lru_cache(maxsize=128)
def feiertage(jahr: int, land: str = STANDARD_LAND) -> dict[date, str]:
    """Gesetzliche Feiertage eines Jahres im Bundesland (landesweit geltende)."""
    o = ostersonntag(jahr)
    t = {date(jahr, 1, 1): "Neujahr", o - timedelta(days=2): "Karfreitag", o + timedelta(days=1): "Ostermontag",
         date(jahr, 5, 1): "Tag der Arbeit", o + timedelta(days=39): "Christi Himmelfahrt",
         o + timedelta(days=50): "Pfingstmontag", date(jahr, 10, 3): "Tag der Deutschen Einheit",
         date(jahr, 12, 25): "1. Weihnachtstag", date(jahr, 12, 26): "2. Weihnachtstag"}
    if land in ("BW", "BY", "ST"):
        t[date(jahr, 1, 6)] = "Heilige Drei Könige"
    if (land == "BE" and jahr >= 2019) or (land == "MV" and jahr >= 2023):
        t[date(jahr, 3, 8)] = "Internationaler Frauentag"
    if land in ("BW", "BY", "HE", "NW", "RP", "SL"):
        t[o + timedelta(days=60)] = "Fronleichnam"
    if land == "SL":
        t[date(jahr, 8, 15)] = "Mariä Himmelfahrt"
    if land == "TH" and jahr >= 2019:
        t[date(jahr, 9, 20)] = "Weltkindertag"
    if land in ("BB", "MV", "SN", "ST", "TH") or (land in ("HB", "HH", "NI", "SH") and jahr >= 2018) or jahr == 2017:
        t[date(jahr, 10, 31)] = "Reformationstag"
    if land in ("BW", "BY", "NW", "RP", "SL"):
        t[date(jahr, 11, 1)] = "Allerheiligen"
    if land == "SN":
        bb = date(jahr, 11, 22)
        while bb.weekday() != 2:
            bb -= timedelta(days=1)
        t[bb] = "Buß- und Bettag"
    return dict(sorted(t.items()))


@dataclass
class Schliesszeit:
    id: str
    titel: str
    von: str                     # ISO
    bis: str                     # ISO, einschließlich

    @property
    def von_d(self) -> date:
        return date.fromisoformat(self.von)

    @property
    def bis_d(self) -> date:
        return date.fromisoformat(self.bis)


def _lesen() -> dict:
    from belegung import speicher

    try:
        d = speicher.lesen(DATEI, {}) or {}
    except Exception:                              # noqa: BLE001
        d = {}
    return d if isinstance(d, dict) else {}


def land() -> str:
    x = str(_lesen().get("land") or STANDARD_LAND)
    return x if x in LAENDER else STANDARD_LAND


def schliesszeiten() -> list[Schliesszeit]:
    erg = []
    for x in _lesen().get("schliesszeiten") or []:
        try:
            s = Schliesszeit(str(x["id"]), str(x.get("titel") or ""), str(x["von"]), str(x["bis"]))
            s.von_d, s.bis_d                       # noqa: B018 – Datum prüfen
            erg.append(s)
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(erg, key=lambda s: s.von)


def _schreiben(d: dict) -> None:
    from belegung import speicher

    speicher.schreiben(DATEI, d)


def land_setzen(wert: str) -> str:
    from .kern import _schritt

    if wert not in LAENDER:
        raise ValueError("Unbekanntes Bundesland.")

    def tun():
        d = _lesen()
        d["land"] = wert
        _schreiben(d)
    _schritt("Bundesland für Feiertage", tun, [DATEI])
    return f"Feiertage: {LAENDER[wert]}"


def schliesszeit_anlegen(titel: str, von: date, bis: date) -> str:
    from .kern import _schritt

    titel = re.sub(r"\s+", " ", (titel or "").strip())[:80]
    if not titel:
        raise ValueError("Bitte eine Bezeichnung eingeben (z. B. „Weihnachtsschließung“).")
    if bis < von:
        raise ValueError("Das Ende liegt vor dem Beginn.")
    if (bis - von).days > 120:
        raise ValueError("Eine Schließzeit darf höchstens 4 Monate dauern.")

    def tun():
        d = _lesen()
        d.setdefault("schliesszeiten", []).append(asdict(Schliesszeit(f"s{datetime.now():%Y%m%d%H%M%S%f}", titel,
                                                                      von.isoformat(), bis.isoformat())))
        _schreiben(d)
    _schritt(f"Schließzeit „{titel}“", tun, [DATEI])
    return f"Schließzeit „{titel}“ eingetragen ({von:%d.%m.} – {bis:%d.%m.%Y})"


def schliesszeit_entfernen(sid: str) -> str:
    from .kern import _schritt

    def tun():
        d = _lesen()
        vorher = d.get("schliesszeiten") or []
        d["schliesszeiten"] = [x for x in vorher if str(x.get("id")) != sid]
        if len(d["schliesszeiten"]) == len(vorher):
            raise ValueError("Diese Schließzeit gibt es nicht mehr.")
        _schreiben(d)
    _schritt("Schließzeit entfernt", tun, [DATEI])
    return "Schließzeit entfernt"


def tage(von: date, bis: date, land_: str | None = None, sz: list[Schliesszeit] | None = None) -> dict[date, str]:
    """Alle Feiertage und Schließtage im Zeitraum: {Tag: „Ostermontag“ / „Schließzeit: Weihnachtsschließung“}."""
    land_ = land_ or land()
    sz = schliesszeiten() if sz is None else sz
    erg: dict[date, str] = {}
    for j in range(von.year, bis.year + 1):
        for t, n in feiertage(j, land_).items():
            if von <= t <= bis:
                erg[t] = n
    for s in sz:
        t = max(s.von_d, von)
        while t <= min(s.bis_d, bis):
            erg[t] = (erg[t] + " · " if t in erg else "") + f"Schließzeit: {s.titel}"
            t += timedelta(days=1)
    return dict(sorted(erg.items()))


def hinweis(tag: date, land_: str | None = None, sz: list[Schliesszeit] | None = None) -> str:
    return tage(tag, tag, land_, sz).get(tag, "")


def termine_im_zeitraum(termine: list[tuple[date, str, str]], heute: date, tage_: int = VORSCHAU_TAGE,
                        land_: str | None = None, sz: list[Schliesszeit] | None = None) -> list[tuple[date, str, list]]:
    """An-/Abreisen (Tag, Art, Name) der nächsten Tage, die auf einen Feiertag oder Schließtag fallen:
    [(Tag, Feiertag, [(Art, Name)…])]."""
    ft = tage(heute, heute + timedelta(days=tage_), land_, sz)
    je: dict[date, list] = {}
    for t, art, name in termine:
        if t in ft:
            je.setdefault(t, []).append((art, name))
    return [(t, ft[t], je[t]) for t in sorted(je)]
