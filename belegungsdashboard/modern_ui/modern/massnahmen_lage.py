"""1.59: Wirtschaftliche Lage als Annahme für die Neuanmeldungen je Maßnahme – wie das Management-Szenario der
Belegungsprognose: „was wäre, wenn es 10 % weniger Zuweisungen gibt?“.

Die Annahme wirkt nur auf den noch offenen Teil der Prognose (erwartete Nachbuchung). Wer schon begonnen hat oder schon
gebucht ist, bleibt – das ist sicher. Ist bleibt Ist. Rein, ohne NiceGUI; gespeichert wird nichts.
"""

from __future__ import annotations

import copy

LAGEN = {0: "wie bisher", -10: "schwache Lage −10 %", -20: "Krise −20 %", 10: "gute Lage +10 %"}
GRENZE = 50                       # höchstens ±50 %


def begrenzen(prozent) -> float:
    try:
        p = float(prozent or 0)
    except (TypeError, ValueError):
        return 0.0
    return max(-GRENZE, min(GRENZE, p))


def _zeile(z, f: float) -> None:
    sicher = (z.ist or 0.0) + (z.gebucht or 0.0)
    for name in ("erwartet", "klein", "gross", "klein95", "gross95"):
        v = getattr(z, name)
        setattr(z, name, sicher + max(0.0, v - sicher) * f)


def anwenden(reihen: dict, prozent: float, jahr: int | None = None) -> dict:
    """Kopie der Reihen mit der Annahme ``prozent`` auf die offenen Prognosezeilen; ``jahr``: „erwartet im nächsten
    Jahr“ wird für dieses Kalenderjahr mitgerechnet."""
    p = begrenzen(prozent)
    if not p:
        return reihen
    f = 1 + p / 100
    erg = {}
    for fam, r in reihen.items():
        neu = copy.deepcopy(r)
        delta = 0.0
        for z in neu.zeilen:
            if z.art != "ist":
                alt = z.erwartet
                _zeile(z, f)
                if jahr is not None and z.hj[0] == jahr:
                    delta += z.erwartet - alt
        if jahr is not None and hasattr(neu, "naechstes_jahr"):
            neu.naechstes_jahr = max(0.0, neu.naechstes_jahr + delta)
        erg[fam] = neu
    return erg


def text(prozent: float) -> str:
    p = begrenzen(prozent)
    if not p:
        return ""
    return (f"Annahme: {p:+.0f} % auf die erwartete Nachbuchung – schon begonnen und schon gebucht bleiben, Ist bleibt "
            "Ist. Simulation, keine echten Daten.")
