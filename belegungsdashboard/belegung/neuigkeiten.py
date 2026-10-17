"""Neuigkeiten: Was im Hintergrund passiert ist – an einem Ort (Glocke oben rechts, Leiste am rechten Rand).

Statt Hinweise einzeln einzublenden (automatisch übernommener Gebäudeplan, UWT zugeteilt, Erinnerung fällig …) sammelt
das Programm sie hier. Antworten auf eigene Klicks (gespeichert, Rückgängig, Fehler) bleiben kurze Einblendungen.
Rein, ohne Qt. Gespeichert in ``importe/neuigkeiten.json`` (höchstens ``MAX`` Einträge).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from . import speicher

DATEI = f"{speicher.IMPORT_ORDNER}/neuigkeiten.json"
MAX = 100


@dataclass
class Neuigkeit:
    id: str
    zeit: datetime
    text: str
    art: str = "info"           # ok | info | warnung | fehler
    ziel: str = ""              # wohin ein Klick führt, z. B. „termine“, „zimmerplan:Aufgaben“
    gelesen: bool = False
    schluessel: str = ""        # gleiche Meldung nicht doppelt (z. B. Erinnerung je Tag)

    def zu_dict(self) -> dict:
        return {"id": self.id, "zeit": self.zeit.isoformat(timespec="seconds"), "text": self.text, "art": self.art,
                "ziel": self.ziel, "gelesen": self.gelesen, "schluessel": self.schluessel}

    @staticmethod
    def aus_dict(d: dict) -> "Neuigkeit":
        return Neuigkeit(d["id"], datetime.fromisoformat(d["zeit"]), d.get("text", ""), d.get("art", "info"),
                         d.get("ziel", ""), bool(d.get("gelesen")), d.get("schluessel", ""))


def laden() -> list[Neuigkeit]:
    """Neueste zuerst."""
    erg = []
    for d in speicher.lesen(DATEI, {}).get("neuigkeiten", []):
        try:
            erg.append(Neuigkeit.aus_dict(d))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(erg, key=lambda n: n.zeit, reverse=True)


def _schreiben(liste: list[Neuigkeit]) -> None:
    liste = sorted(liste, key=lambda n: n.zeit, reverse=True)[:MAX]
    speicher.schreiben(DATEI, {"neuigkeiten": [n.zu_dict() for n in liste]})


def hinzufuegen(text: str, art: str = "info", ziel: str = "", schluessel: str = "",
                jetzt: datetime | None = None) -> Neuigkeit | None:
    """Neue Meldung; mit ``schluessel`` nur einmal (None, wenn es sie schon gibt)."""
    alle = laden()
    if schluessel and any(n.schluessel == schluessel for n in alle):
        return None
    n = Neuigkeit(uuid.uuid4().hex[:10], jetzt or datetime.now(), text, art, ziel, False, schluessel)
    _schreiben([n] + alle)
    return n


def ungelesen() -> int:
    return sum(1 for n in laden() if not n.gelesen)


def gelesen_setzen(nid: str | None = None) -> None:
    """Eine (``nid``) oder alle als gelesen markieren."""
    alle = laden()
    for n in alle:
        if nid is None or n.id == nid:
            n.gelesen = True
    _schreiben(alle)


def entfernen(nid: str | None = None) -> None:
    """Eine (``nid``) oder alle entfernen."""
    _schreiben([n for n in laden() if nid is not None and n.id != nid])
