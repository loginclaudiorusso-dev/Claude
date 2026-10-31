"""Standorte: Goslar, Bad Pyrmont, Weser-Ems – die Verwaltung (Zimmer, Anreisen, Reinigung …) je Standort getrennt.

Jeder Standort hat seinen eigenen Datenordner: Goslar bleibt, wo die Daten immer lagen; Bad Pyrmont und Weser-Ems
liegen darunter in ``Standorte/BP`` bzw. ``Standorte/WE`` – mit eigenem Gebäudeplan, eigenen Anreiselisten, Mängeln,
Sicherungen und Verlauf. Das Hauptprogramm wird dafür nicht geändert: Die neue Oberfläche lenkt nur zur Laufzeit
um, wohin es liest und schreibt.

* **Datenordner:** ``datenordner()`` ersetzt die gleichnamige Funktion des Hauptprogramms. Sie liefert den Ordner
  des gewählten Standorts. Die Prognose (Auswertung) liest mit ``haupt()`` weiter aus dem Goslar-Ordner – dort
  liegen Pivot, Kapazitäten, Statistik und die Goslar-Listen, aus denen sie rechnet. Sie bleibt so, wie sie war.
* **Gebäudeplan-Format:** In Goslar heißen die Zimmer „GS-3.2-111“ (Häuser „GS-Haus-3.2“), in Bad Pyrmont
  „BP-A 103“ (Häuser „A Gebäude“), in Weser-Ems „WE-A 202 R“ (Häuser „Internat A“). Etagen sind überall gleich.
* **Regeln:** Die Zuteil-Regeln des Hauptprogramms sind auf Goslar zugeschnitten (Häuser 2, 3.1–3.3, 6). An den
  anderen Standorten gelten zunächst neutrale Regeln: alle Zimmer für alle Gruppen, Doppelzimmer nur für UWT und
  Gäste, Gästezimmer nur für Gäste, Tier-Zimmer, „nur Männer“ und „außer Betrieb“ wie in den Zimmer-Stammdaten
  markiert. Eigene Regeln je Standort kommen nach und nach dazu.

In Goslar ist alles exakt wie vorher. Rein, ohne NiceGUI.
"""

from __future__ import annotations

import json
import re
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from belegung import konfig


@dataclass(frozen=True)
class Standort:
    kurz: str             # GS | BP | WE
    name: str             # Goslar
    schluessel: str       # „BFW GS“ – wie in der Prognose
    zimmer_muster: str    # Zimmer-ID im Gebäudeplan
    haus_muster: str      # Haus-Überschrift im Gebäudeplan
    beispiel: str         # Beispiel für die Zimmereingabe


STANDORTE: dict[str, Standort] = {
    "GS": Standort("GS", "Goslar", "BFW GS", r"^GS-([\d.]+)-([A-Z]?\d+)$", r"^GS-Haus-([\d.]+)$", "3.2-111"),
    "BP": Standort("BP", "Bad Pyrmont", "BFW BP", r"^BP-([A-Z])\s+([0-9U][\d.]*)$", r"^([A-Z]) Gebäude$", "A 103"),
    "WE": Standort("WE", "Weser-Ems", "BFW WE", r"^WE-([A-Z])\s+(\d\S*(?:\s+\S.*)?)$", r"^Internat ([A-Z])$", "A 202 R"),
}
STANDARD = "GS"
_WAHL = "importe/modern_standort.json"          # im Goslar-Ordner: zuletzt gewählter Standort

_BASIS = konfig.datenordner                     # Original: BELEGUNG_DATEN bzw. Programmordner (= Goslar)
_lokal = threading.local()
_zustand = {"aktiv": STANDARD, "installiert": False}
_ORIGINAL: dict = {}


def aktiv() -> Standort:
    return STANDORTE[_zustand["aktiv"]]


def ist_goslar() -> bool:
    return _zustand["aktiv"] == "GS"


def ordner(kurz: str) -> Path:
    basis = _BASIS()
    return basis if kurz == "GS" else basis / "Standorte" / kurz


def datenordner() -> Path:
    """Ersatz für ``konfig.datenordner``: Ordner des gewählten Standorts (in ``haupt()``: Goslar)."""
    return getattr(_lokal, "ordner", None) or ordner(_zustand["aktiv"])


@contextmanager
def haupt():
    """Für die Prognose und ihre Quellen (Pivot, Kapazitäten, Statistik): immer aus dem Goslar-Ordner lesen."""
    vorher = getattr(_lokal, "ordner", None)
    _lokal.ordner = _BASIS()
    try:
        yield
    finally:
        _lokal.ordner = vorher


def im_haupt(fn):
    """Funktion immer im Goslar-Ordner ausführen (Dekorator für die Prognose-Quellen)."""
    def huelle(*args, **kwargs):
        with haupt():
            return fn(*args, **kwargs)
    huelle.__name__, huelle.__doc__ = fn.__name__, fn.__doc__
    return huelle


# ---- Wahl merken ------------------------------------------------------------------------

def gemerkt() -> str:
    try:
        k = json.loads((_BASIS() / _WAHL).read_text(encoding="utf-8")).get("standort", STANDARD)
    except (OSError, ValueError):
        return STANDARD
    return k if k in STANDORTE else STANDARD


def merken(kurz: str) -> None:
    p = _BASIS() / _WAHL
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"standort": kurz}), encoding="utf-8")
    except OSError:
        pass


# ---- Umschalten -------------------------------------------------------------------------

def installieren() -> None:
    """Einmal beim Start: die Datenordner-Funktion des Hauptprogramms durch ``datenordner`` ersetzen."""
    if _zustand["installiert"]:
        return
    from belegung import datensicherung, erinnerung, speicher

    for mod in (konfig, speicher, datensicherung, erinnerung):
        mod.datenordner = datenordner
    _zustand["installiert"] = True


def waehlen(kurz: str, merken_: bool = True) -> Standort:
    """Standort wechseln: Ordner, Gebäudeplan-Format und Regeln umstellen. Das Rückgängig gilt nur je Standort und
    wird deshalb geleert."""
    from belegung import aenderungen

    if kurz not in STANDORTE:
        raise ValueError(f"Unbekannter Standort „{kurz}“.")
    installieren()
    _zustand["aktiv"] = kurz
    if kurz != "GS":
        try:
            ordner(kurz).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    _anpassen(STANDORTE[kurz])
    aenderungen.verlauf_leeren()
    if merken_:
        merken(kurz)
    return STANDORTE[kurz]


def _erlaubt_neutral(z, gruppe: str) -> bool:
    """Neutrale Regel (Standorte ohne eigene Regeln): Gästezimmer nur für Gäste, Doppelzimmer nur UWT/Gäste."""
    from belegung import zimmerplan as zp

    if z.gaeste and gruppe != "Gast":
        return False
    return not zp.nur_doppel(z, gruppe)


def _anpassen(s: Standort) -> None:
    """Goslar-Besonderheiten des Hauptprogramms je Standort aus- bzw. wieder einschalten (nur im Arbeitsspeicher)."""
    from belegung import gebaeudeplan, zimmerplan as zp

    if not _ORIGINAL:
        _ORIGINAL.update(zimmer=gebaeudeplan._ZIMMER, haus=gebaeudeplan._HAUS, gaeste=zp.GAESTEZIMMER,
                         erlaubt=zp.erlaubt, mitgeliefert=zp.mitgelieferte_zimmer, haus_sort=zp._haus_sort)
    if s.kurz == "GS":
        gebaeudeplan._ZIMMER, gebaeudeplan._HAUS = _ORIGINAL["zimmer"], _ORIGINAL["haus"]
        zp.GAESTEZIMMER, zp.erlaubt, zp.mitgelieferte_zimmer = (_ORIGINAL["gaeste"], _ORIGINAL["erlaubt"],
                                                                 _ORIGINAL["mitgeliefert"])
        zp._haus_sort = _ORIGINAL["haus_sort"]
        return
    gebaeudeplan._ZIMMER, gebaeudeplan._HAUS = re.compile(s.zimmer_muster), re.compile(s.haus_muster)
    zp.GAESTEZIMMER = []                        # Goslar: Gästezimmer Haus 2, 6. OG – gibt es hier nicht
    zp.erlaubt = _erlaubt_neutral
    zp.mitgelieferte_zimmer = lambda: []        # Zimmer kommen nur aus dem eigenen Gebäudeplan
    zp._haus_sort = _haus_sort                  # Häuser A, B, C … in alphabetischer Reihenfolge


def _haus_sort(h: str) -> float:
    try:
        return float(h)
    except ValueError:
        return 100 + sum(ord(c) / 1000 ** i for i, c in enumerate(h.upper()))


def daten_text(kurz: str) -> str:
    """Kurz für die Auswahl: wie viele Zimmer der Standort kennt (aus dem gespeicherten Gebäudeplan)."""
    if kurz == "GS":
        return "Hauptstandort"
    p = ordner(kurz) / "importe" / "gebaeudeplan.json"
    try:
        n = len(json.loads(p.read_text(encoding="utf-8")).get("zimmer", []))
    except (OSError, ValueError):
        return "noch kein Gebäudeplan"
    return f"{n} Zimmer"


# ---- Zimmer-Kurzform --------------------------------------------------------------------

_PRAEFIX = re.compile(r"^(?:GS|BP|WE)-")


def kurz(zid: str) -> str:
    """„GS-3.2-111“ → „3.2-111“, „BP-A 103“ → „A 103“, „WE-A 202 R“ → „A 202 R“."""
    return _PRAEFIX.sub("", zid or "")


def zimmer_aus_text(zimmer_ids, text: str) -> str | None:
    """Freie Eingabe → Zimmer-ID des aktiven Standorts, ohne Rücksicht auf Leerzeichen, Bindestriche und Groß/Klein
    („a103“, „A-103“, „BP-A 103“ → „BP-A 103“; „a 202r“ → „WE-A 202 R“)."""
    def norm(t: str) -> str:
        return re.sub(r"[\s\-_/]+", "", kurz(t.strip().upper()))
    ziel = norm(text or "")
    if not ziel:
        return None
    return next((zid for zid in zimmer_ids if norm(zid) == ziel), None)
