"""1.65: Abreisen vollständig – aus dem Zimmerplan UND aus der Anreiseliste.

Die Abreiseliste des Hauptprogramms (``cockpit.abreiseliste``) kennt nur das Ende einer Zimmerbelegung. Wird die
Abreise in der Anreiseliste geändert (EMR: Sonntag bis Mittwoch, vorzeitiges Ende per Mail …), läuft die Belegung im
Plan noch bis zum alten Datum weiter – die Person fehlte dann in „Abreisen heute / diese Woche“, obwohl der Termin
„Abreise“ sie richtig meldete.

Hier kommen alle Personen dazu, deren Abreise laut Anreiseliste im Zeitraum liegt und die im Internat wohnen – mit
ihrem Zimmer (Belegung am Abreisetag, sonst die zeitlich nächste) und dem Hinweis, wie lange der Plan sie noch führt.
Rein (ohne Oberfläche), damit testbar.
"""

from __future__ import annotations

from datetime import date

from belegung import anreiseliste
from belegung import cockpit

ART_LISTE = "liste"          # Abreise nur laut Anreiseliste (Plan läuft länger oder kein Zimmer)


def _woerter(name: str) -> frozenset:
    return frozenset((name or "").replace(",", " ").lower().split())


def ergaenzen(aus_plan: list, personen: list, lage, von: date, bis: date) -> list:
    """``aus_plan`` (cockpit.Abreise) + Abreisen laut Anreiseliste, die dort fehlen – nach Tag und Name sortiert."""
    from .termin_zimmer import zimmer_von

    schon = {a.schluessel for a in aus_plan if getattr(a, "schluessel", "")}
    namen = {(a.tag, _woerter(a.name)) for a in aus_plan}
    erg = list(aus_plan)
    for p in personen:
        if not p.abreise or not (von <= p.abreise <= bis) or not p.internat:
            continue
        if p.schluessel in schon or (p.abreise, _woerter(p.name)) in namen:
            continue
        zid = zimmer_von(lage, p.schluessel, p.name, p.abreise)
        erg.append(cockpit.Abreise(p.abreise, p.name, p.massnahme or p.gruppe, zid or "", anreiseliste.ankunft(p),
                                   ART_LISTE, None, p.schluessel))
    return sorted(erg, key=lambda a: (a.tag, a.zimmer or "~", a.name))


def plan_bis(lage, zid: str, schluessel: str, name: str) -> date | None:
    """Bis wann der Plan die Person im Zimmer führt (für den Hinweis)."""
    for b in (getattr(lage, "belegungen", None) or {}).get(zid, []):
        if b.art in ("belegt", "geplant") and ((schluessel and b.person == schluessel)
                                                 or _woerter(b.name) == _woerter(name)):
            return b.bis
    return None


def abreisen(stand, von: date, bis: date, personen: list | None = None) -> list:
    """Alle Abreisen von … bis – Plan und Anreiseliste. Fehler beim Lesen der Liste → nur der Plan."""
    plan = cockpit.abreiseliste(stand, von, bis)
    try:
        if personen is None:
            personen, _ = anreiseliste.laden()
        return ergaenzen(plan, personen, stand.lage, von, bis)
    except Exception:                                   # noqa: BLE001 – lieber die Plan-Liste als gar keine
        return plan
