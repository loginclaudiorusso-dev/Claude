"""0.90: Nichtanreisen als eigene Schicht über der Anreiseliste. Rein, ohne NiceGUI."""

from __future__ import annotations

# 0.90: Nichtanreisen als eigene Schicht – eine neu eingelesene Anreiseliste setzt „Internat“ wieder auf ja; beim Laden
# gewinnt die Handeingabe (Schlüssel = TN-ID bzw. Name + Anreise; eine neue Anreise ist ein neuer Schlüssel).
NICHTANREISE_DATEI = "modern_nichtanreise.json"


def nichtanreisen() -> dict[str, dict]:
    from belegung import speicher

    roh = speicher.lesen(NICHTANREISE_DATEI, {}) or {}
    return {k: v for k, v in roh.items() if isinstance(v, dict)} if isinstance(roh, dict) else {}


def nichtanreise_installieren() -> None:
    from belegung import anreiseliste

    if getattr(anreiseliste.laden, "_nichtanreise", False):
        return
    orig = anreiseliste.laden

    def laden():
        personen, listen = orig()
        na = nichtanreisen()
        if na:
            for p in personen:
                if p.internat and p.schluessel in na and na[p.schluessel].get("anreise") == p.anreise.isoformat():
                    p.internat = False
        return personen, listen
    laden._nichtanreise = True
    laden._orig = orig
    anreiseliste.laden = laden
