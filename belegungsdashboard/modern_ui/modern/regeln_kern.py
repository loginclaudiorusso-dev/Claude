"""Haus 6 (Goslar): Bad über den Flur und Aufteilung je Etage – zur Laufzeit, das Hauptprogramm bleibt unverändert.

Grundriss je Etage (ein Flur, 9 Zimmer): Die Zimmer **x01, x02, x08, x09** haben das Bad über den Flur und bleiben
**nur für Männer**; die übrigen 5 haben ein eigenes Bad. (Das Hauptprogramm führt auch x05 als „Bad über den Flur“ –
das ist korrigiert. Eigene Angaben in den Zimmer-Stammdaten gehen weiter vor.)

Schaltbar (Einstellungen → „Haus 6: Aufteilung je Etage“), aus = bisherige Regeln (nur Mieter und UWT):

* **Hauptmaßnahmen** dürfen in die 5 Zimmer mit eigenem Bad (Haus 6 entlastet Haus 2).
* **Renovierte Etagen** (alle Zimmer mit Renovierungsvermerk): Mieter bevorzugt in x01/x02, UWT bevorzugt in x08/x09,
  die Zimmer mit eigenem Bad bleiben möglichst für Hauptmaßnahmen frei. Nichts ist reserviert – es sind Vorrang-Punkte
  bei der Zimmerwahl, keine Sperren.

Wichtig: Das Hauptprogramm kennt diese Aufteilung nicht – wer dort zuteilt, bekommt die alten Haus-6-Regeln.
Rein, ohne NiceGUI.
"""

from __future__ import annotations

from belegung import speicher
from belegung import zimmerplan as zp

EINSTELLUNG = "modern_haus6_aufteilung"
BAD_UEBER_FLUR = (1, 2, 8, 9)
MIETER_ZIMMER = (1, 2)
UWT_ZIMMER = (8, 9)
HAUPT = "Reha"                                    # Gruppe „Hauptmaßnahme“

_ORIG: dict = {}
_RENOVIERT: set[tuple[str, str]] = set()          # (Haus, Etage) – alle Zimmer mit Renovierungsvermerk
_CACHE: dict = {"mtime": None, "an": False}
_ERZWINGEN: dict = {"wert": None}                  # Vorschau: Regel vorübergehend an/aus


def an() -> bool:
    """Eingeschaltet? (aus den Einstellungen, nur neu gelesen, wenn die Datei sich geändert hat – auch nach Rückgängig)"""
    if _ERZWINGEN["wert"] is not None:
        return _ERZWINGEN["wert"]
    try:
        mtime = speicher.pfad(speicher.EINSTELLUNGEN).stat().st_mtime_ns
    except OSError:
        mtime = 0
    if mtime != _CACHE["mtime"]:
        _CACHE.update(mtime=mtime, an=bool(speicher.einstellungen().get(EINSTELLUNG, False)))
    return _CACHE["an"]


def bad_ueber_flur(z) -> bool:
    return z.haus == "6" and z.nummer % 100 in BAD_UEBER_FLUR


def _standard_zimmer(plan_zimmer):
    erg = _ORIG["standard"](plan_zimmer)
    for z in erg:
        if z.haus == "6":
            z.nur_maenner = bad_ueber_flur(z)      # x05 hat ein eigenes Bad
    return erg


def _erlaubt(z, gruppe: str) -> bool:
    if an() and (gruppe == HAUPT and z.haus == "6" and z.aktiv and not z.nur_maenner and not z.gaeste and z.betten == 1):
        return True
    return _ORIG["erlaubt"](z, gruppe)


def _wert(z, b) -> list:
    d = list(_ORIG["wert"](z, b))
    if z.haus != "6" or not an():
        return d
    nr, renoviert = z.nummer % 100, (z.haus, z.etage) in _RENOVIERT
    if b.gruppe == HAUPT and not z.nur_maenner:
        d.append((1, "Haus 6 mit eigenem Bad – entlastet Haus 2"))
    if renoviert and b.gruppe == "Mieter" and nr in MIETER_ZIMMER:
        d.append((3, "Mieter-Zimmer der renovierten Etage (x01/x02)"))
    if renoviert and b.gruppe == "UWT" and nr in UWT_ZIMMER:
        d.append((3, "UWT-Zimmer der renovierten Etage (x08/x09)"))
    if renoviert and b.gruppe in ("Mieter", "UWT") and not bad_ueber_flur(z):
        d.append((-2, "eigenes Bad für Hauptmaßnahmen freihalten (renovierte Etage)"))
    return d


def anwenden(orig: dict | None = None) -> None:
    """Goslar: Haus-6-Korrektur immer, die neue Aufteilung nur wenn eingeschaltet. ``orig`` = Originale des
    Hauptprogramms (von standort_kern); ohne Angabe die beim ersten Aufruf vorgefundenen."""
    if not _ORIG:
        _ORIG.update(standard=zp.standard_zimmer, erlaubt=zp.erlaubt, wert=zp.zimmer_wert_details)
    if orig:
        _ORIG.update({k: orig[k] for k in ("standard", "erlaubt", "wert") if k in orig})
    zp.standard_zimmer = _standard_zimmer
    zp.erlaubt, zp.zimmer_wert_details = _erlaubt, _wert          # wirken nur, wenn eingeschaltet (an())


def zuruecksetzen() -> None:
    """Originale wiederherstellen (andere Standorte, Tests)."""
    if _ORIG:
        zp.standard_zimmer, zp.erlaubt, zp.zimmer_wert_details = _ORIG["standard"], _ORIG["erlaubt"], _ORIG["wert"]


def aktualisieren(stand: zp.Planstand) -> set[tuple[str, str]]:
    """Welche Haus-6-Etagen gelten als renoviert? (bei jedem Laden; alle Zimmer der Etage mit Renovierungsvermerk)"""
    etagen: dict[tuple[str, str], list] = {}
    for z in stand.zimmer:
        if z.haus == "6" and z.aktiv:
            etagen.setdefault((z.haus, z.etage), []).append(z)
    _RENOVIERT.clear()
    _RENOVIERT.update(k for k, zs in etagen.items() if zs and all(z.renoviert for z in zs))
    return set(_RENOVIERT)


def setzen(wert: bool) -> str:
    from .kern import _schritt

    _schritt("Haus 6: Aufteilung " + ("an" if wert else "aus"), lambda: speicher.einstellung_setzen(EINSTELLUNG, bool(wert)),
             [speicher.EINSTELLUNGEN])
    return ("Haus 6: Hauptmaßnahmen in Zimmern mit eigenem Bad, Vorrang für Mieter (x01/x02) und UWT (x08/x09) auf "
            "renovierten Etagen" if wert else "Haus 6: wieder die bisherigen Regeln (nur Mieter und UWT)")


def vorschau(stand: zp.Planstand, heute, wochen: int = 8) -> list[tuple[str, str, str, str]]:
    """Was würde sich an den Vorschlägen für Anreisen ohne Zimmer ändern? (Name, Anreise, vorher, nachher)"""
    from datetime import timedelta

    from . import kern

    if zp.erlaubt is not _erlaubt:
        anwenden()
    tage = sorted({b.von.isoformat() for b in stand.bedarf if heute <= b.von <= heute + timedelta(weeks=wochen)
                   and not stand.zugewiesen(b.schluessel)})

    def vorschlaege(mit: bool) -> dict:
        _ERZWINGEN["wert"] = mit
        return {z.schluessel: (z.name, tag, z.vorschlag or "") for tag in tage for z in kern.zeilen(stand, tag, heute)
                if not z.gespeichert}
    try:
        aus, ein = vorschlaege(False), vorschlaege(True)
    finally:
        _ERZWINGEN["wert"] = None                  # wieder wie eingestellt
    return [(n, t, kern.kurz(v) if v else "–", kern.kurz(ein[k][2]) if ein.get(k, ("", "", ""))[2] else "–")
            for k, (n, t, v) in aus.items() if ein.get(k, (n, t, v))[2] != v]
