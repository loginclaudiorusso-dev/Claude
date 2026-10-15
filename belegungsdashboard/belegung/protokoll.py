"""Änderungsprotokoll der Zimmerplanung: wer wann wen in welches Zimmer geplant, umgeplant oder entfernt hat.

Rein, ohne Qt. Gespeichert werden höchstens ``MAX`` Einträge (die ältesten fallen weg).
"""

from __future__ import annotations

import getpass
import os
from datetime import datetime

from . import speicher

DATEI = f"{speicher.IMPORT_ORDNER}/protokoll.json"
MAX = 3000


def benutzer() -> str:
    try:
        return os.environ.get("USERNAME") or getpass.getuser()
    except Exception:
        return ""


def eintragen(eintraege: list[dict]) -> None:
    """eintraege: {aktion, name, person, alt, neu, von, quelle} – Zeit und Benutzer werden ergänzt."""
    if not eintraege:
        return
    zeit, wer = datetime.now().isoformat(timespec="seconds"), benutzer()
    alle = speicher.lesen(DATEI, {}).get("eintraege", [])
    alle += [{"zeit": zeit, "wer": wer, **e} for e in eintraege]
    speicher.schreiben(DATEI, {"eintraege": alle[-MAX:]})


def laden(anzahl: int | None = None) -> list[dict]:
    """Neueste zuerst."""
    alle = list(reversed(speicher.lesen(DATEI, {}).get("eintraege", [])))
    return alle[:anzahl] if anzahl else alle
