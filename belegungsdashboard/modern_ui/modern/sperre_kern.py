"""Sperre vorzeitig beenden (0.61): Ein Zimmer ist laut Gebäudeplan (Belegungssystem) noch gesperrt, z. B. wegen
Renovierung, wird aber früher fertig – und im Belegungssystem lässt sich das Ende nicht ändern. Hier wird eingetragen,
ab wann das Zimmer wieder frei ist („fertig renoviert ab …“). Rein, ohne NiceGUI.

Die Angabe liegt in ``modern_sperre_ende.json`` im Datenordner des Standorts (mit gesichert). Beim Laden wird jede
Sperre des Zimmers, die über diesen Tag hinausreicht, an dieser Stelle beendet – Planung, Suche, Auslastung und
Mietverträge sehen das Zimmer ab dann als frei. Der Gebäudeplan selbst und das Hauptprogramm bleiben unverändert (das
bisherige PySide-Programm sieht die Sperre deshalb weiter). „Gehört nicht zum Internat“ wird nie verkürzt.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from belegung import speicher
from belegung import zimmerplan as zp

DATEI = "modern_sperre_ende.json"
NIE = "nicht im Internat"
_ORIG: dict = {}
_GEKUERZT: dict[str, list] = {}        # Zimmer → [(Sperre von, bis laut Gebäudeplan, Grund)] beim letzten Laden


@dataclass
class Sperre:
    von: date
    bis: date                          # laut Gebäudeplan
    grund: str
    frei_ab: date | None = None        # eigene Angabe: ab diesem Tag frei

    @property
    def text(self) -> str:
        t = f"gesperrt {self.von:%d.%m.%Y} – {self.bis:%d.%m.%Y}" + (f" ({self.grund})" if self.grund else "")
        return t + (f" · früher frei ab {self.frei_ab:%d.%m.%Y}" if self.frei_ab else "")


def eintraege() -> dict[str, dict]:
    roh = speicher.lesen(DATEI, {}) or {}
    return {k: v for k, v in (roh.get("zimmer") or {}).items() if isinstance(v, dict) and v.get("frei_ab")}


def frei_ab(zid: str) -> date | None:
    e = eintraege().get(zid)
    try:
        return date.fromisoformat(e["frei_ab"]) if e else None
    except (KeyError, ValueError):
        return None


def _kuerzen(lage) -> None:
    _GEKUERZT.clear()
    for zid, e in eintraege().items():
        try:
            ab = date.fromisoformat(e["frei_ab"])
        except (KeyError, ValueError):
            continue
        alt = lage.belegungen.get(zid)
        if not alt:
            continue
        neu = []
        for b in alt:
            if b.art != "gesperrt" or b.grund == NIE or b.bis < ab:
                neu.append(b)
                continue
            _GEKUERZT.setdefault(zid, []).append((b.von, b.bis, b.grund))
            if b.von < ab:
                neu.append(replace(b, bis=ab - timedelta(days=1)))
        lage.belegungen[zid] = neu


def _lage_bauen(*args, **kwargs):
    lage = _ORIG["lage_bauen"](*args, **kwargs)
    try:
        _kuerzen(lage)
    except Exception:                              # noqa: BLE001 – die eigene Angabe darf das Laden nie verhindern
        pass
    return lage


def installieren() -> None:
    if _ORIG:
        return
    _ORIG["lage_bauen"] = zp.lage_bauen
    zp.lage_bauen = _lage_bauen


def zuruecksetzen() -> None:
    if _ORIG:
        zp.lage_bauen = _ORIG.pop("lage_bauen")


def sperren(stand, zid: str, heute: date) -> list[Sperre]:
    """Laufende und kommende Sperren des Zimmers – mit dem Ende laut Gebäudeplan und der eigenen Angabe."""
    ab = frei_ab(zid)
    erg = []
    gekuerzt = {(v, g) for v, _b, g in _GEKUERZT.get(zid, [])}
    for v, b, g in _GEKUERZT.get(zid, []):
        if b >= heute:
            erg.append(Sperre(v, b, g, ab))
    for b in stand.lage.belegungen.get(zid, []):
        if b.art == "gesperrt" and b.grund != NIE and b.bis >= heute and (b.von, b.grund) not in gekuerzt:
            erg.append(Sperre(b.von, b.bis, b.grund, None))
    return sorted(erg, key=lambda s: s.von)


def setzen(zid: str, ab: date | None, notiz: str = "") -> str:
    roh = speicher.lesen(DATEI, {}) or {}
    alle = dict(roh.get("zimmer") or {})
    if ab is None:
        alle.pop(zid, None)
    else:
        alle[zid] = {"frei_ab": ab.isoformat(), "notiz": notiz.strip(), "am": datetime.now().isoformat(timespec="seconds")}
    speicher.schreiben(DATEI, {"zimmer": alle})
    kurz = zid.removeprefix("GS-")
    return f"{kurz}: frei ab {ab:%d.%m.%Y} (fertig renoviert)" if ab else f"{kurz}: Sperre wieder wie im Gebäudeplan"


def setzen_schritt(zid: str, ab: date | None, notiz: str = "") -> str:
    from belegung import protokoll

    from .kern import _schritt

    out = []

    def tun():
        out.append(setzen(zid, ab, notiz))
        protokoll.eintragen([{"aktion": "Sperre früher beendet" if ab else "Sperre wie im Gebäudeplan", "name": "",
                              "person": "", "alt": "", "neu": ab.isoformat() if ab else "", "zimmer": zid,
                              "von": ab.isoformat() if ab else "", "quelle": "Zimmer" + (f" · {notiz}" if notiz else "")}])
    _schritt(f"Zimmer {zid.removeprefix('GS-')}: " + (f"frei ab {ab:%d.%m.%Y}" if ab else "Sperre zurück"), tun, [DATEI])
    return out[0]
