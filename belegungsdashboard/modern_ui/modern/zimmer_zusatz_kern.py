"""Zimmer hinzufügen und entfernen (0.53). Rein, ohne NiceGUI.

Die Zimmer kommen aus dem Gebäudeplan (bzw. der mitgelieferten Liste des Hauptprogramms). Fehlt dort ein Zimmer,
wird es hier **zusätzlich** angelegt (``modern_zimmer_zusatz.json`` im Datenordner des Standorts, mit gesichert) und beim
Laden in die Zimmerliste eingehängt – Belegung, Planung, Suche und Statistik sehen es wie jedes andere Zimmer.
Merkmale (Flur, Tier, Gäste, Boden …) pflegt man danach wie gewohnt in den Zimmer-Stammdaten.

**Entfernen**: ein selbst angelegtes Zimmer wird gelöscht (nur ohne laufende oder künftige Planung). Ein Zimmer aus dem
Gebäudeplan lässt sich nicht löschen – es wird auf „gehört nicht zum Internat“ gesetzt (Stammdaten ``aktiv``) und ist
damit aus Planung und Auslastung heraus; zurückholen geht jederzeit.

Hinweis: Das bisherige PySide-Programm kennt die zusätzlichen Zimmer nicht – sie erscheinen nur in der neuen Oberfläche.
"""

from __future__ import annotations

import re
from datetime import date
from types import SimpleNamespace

from belegung import gebaeudeplan, speicher
from belegung import zimmerplan as zp

DATEI = "modern_zimmer_zusatz.json"
_ORIG: dict = {}


def liste() -> list[dict]:
    return [dict(z) for z in (speicher.lesen(DATEI, {}).get("zimmer") or [])]


def _plan_zimmer() -> list[gebaeudeplan.PlanZimmer]:
    return [gebaeudeplan.PlanZimmer(z["id"], z["haus"], z["etage"], z["nr"], int(z.get("betten") or 1)) for z in liste()]


def _mit_zusatz(plan):
    """Plan (oder None) → Objekt mit ``zimmer`` = Plan-Zimmer + zusätzliche (nur, die noch fehlen)."""
    basis = list(plan.zimmer) if plan else list(zp.mitgelieferte_zimmer())
    ids = {p.id for p in basis}
    extra = [p for p in _plan_zimmer() if p.id not in ids]
    if not extra:
        return plan
    return SimpleNamespace(zimmer=basis + extra)


def installieren() -> None:
    """``zimmerplan.stammdaten`` und ``stammdaten_speichern`` so erweitern, dass zusätzliche Zimmer dazugehören."""
    if _ORIG:
        return
    _ORIG.update(stammdaten=zp.stammdaten, speichern=zp.stammdaten_speichern)
    zp.stammdaten = lambda plan: _ORIG["stammdaten"](_mit_zusatz(plan))
    zp.stammdaten_speichern = lambda zimmer, plan: _ORIG["speichern"](zimmer, _mit_zusatz(plan))


def zuruecksetzen() -> None:
    if _ORIG:
        zp.stammdaten, zp.stammdaten_speichern = _ORIG["stammdaten"], _ORIG["speichern"]
        _ORIG.clear()


def zimmer_id(haus: str, nr: str) -> str:
    """Kennung wie im Gebäudeplan des Standorts (Goslar „GS-2-201“, Bad Pyrmont „BP-A 103“, Weser-Ems „WE-A 202“)."""
    from . import standort_kern

    k = standort_kern.aktiv().kurz
    return f"{k}-{haus}-{nr}" if k == "GS" else f"{k}-{haus} {nr}"


def etage_vorschlag(nr: str) -> str:
    m = re.match(r"^([A-Z]?)(\d+)", nr)
    if not m:
        return "E"
    if m.group(1):
        return m.group(1)
    n = int(m.group(2))
    return str(n // 100) if n >= 100 else "E"


def hinzufuegen(haus: str, etage: str, nr: str, betten: int = 1) -> str:
    haus, etage, nr = str(haus).strip(), str(etage).strip(), str(nr).strip()
    if not haus or not nr:
        raise ValueError("Bitte Haus und Zimmernummer angeben.")
    if not re.fullmatch(r"[\w.]+", haus) or not re.fullmatch(r"[\w.\- ]+", nr):
        raise ValueError("Haus und Nummer bitte nur mit Buchstaben, Ziffern, Punkt oder Bindestrich.")
    if not 1 <= int(betten) <= 4:
        raise ValueError("Betten: 1 bis 4.")
    zid = zimmer_id(haus, nr)
    if any(z.id == zid for z in zp.laden().zimmer):
        raise ValueError(f"Zimmer {haus}-{nr} gibt es schon.")
    roh = speicher.lesen(DATEI, {})
    roh.setdefault("zimmer", []).append({"id": zid, "haus": haus, "etage": etage or etage_vorschlag(nr), "nr": nr,
                                         "betten": int(betten), "angelegt": date.today().isoformat()})
    speicher.schreiben(DATEI, roh)
    return f"Zimmer {haus}-{nr} angelegt ({int(betten)} Bett{'en' if int(betten) > 1 else ''})"


def _belegt_kuenftig(zid: str) -> list[str]:
    st = zp.laden()
    heute = date.today()
    erg = [f"{z.get('name', '')} ab {z.get('von', '')}" for z in st.zuweisungen if z.get("zimmer") == zid
           and str(z.get("bis") or "") >= heute.isoformat()]
    erg += [f"{b.name or b.art} ab {b.von:%d.%m.%Y}" for b in st.lage.belegungen.get(zid, []) if b.bis >= heute]
    return erg


def entfernen(zid: str) -> str:
    """Selbst angelegtes Zimmer löschen; Zimmer aus dem Gebäudeplan auf „gehört nicht zum Internat“ setzen."""
    eigen = [z for z in liste() if z["id"] == zid]
    if eigen:
        if belegt := _belegt_kuenftig(zid):
            raise ValueError("Das Zimmer ist noch verplant oder belegt (" + "; ".join(belegt[:3]) + ") – erst umplanen.")
        roh = speicher.lesen(DATEI, {})
        roh["zimmer"] = [z for z in roh.get("zimmer") or [] if z["id"] != zid]
        speicher.schreiben(DATEI, roh)
        return f"Zimmer {eigen[0]['haus']}-{eigen[0]['nr']} gelöscht"
    st = zp.laden()
    z = next((x for x in st.zimmer if x.id == zid), None)
    if z is None:
        raise ValueError("Zimmer nicht gefunden.")
    z.aktiv = False
    zp.stammdaten_speichern(st.zimmer, st.plan)
    return f"Zimmer {z.kurz} gehört nicht mehr zum Internat (Stammdaten: „gehört zum Internat“ wieder einschalten)"


def ist_zusatz(zid: str) -> bool:
    return any(z["id"] == zid for z in liste())


def hinzufuegen_schritt(haus: str, etage: str, nr: str, betten: int = 1) -> str:
    from .kern import _schritt

    out = []
    _schritt(f"Zimmer angelegt: {haus}-{nr}", lambda: out.append(hinzufuegen(haus, etage, nr, betten)), [DATEI])
    return out[0]


def entfernen_schritt(zid: str) -> str:
    from .kern import _schritt

    out = []
    _schritt(f"Zimmer entfernt: {zid}", lambda: out.append(entfernen(zid)), [DATEI, zp.STAMM_DATEI])
    return out[0]
