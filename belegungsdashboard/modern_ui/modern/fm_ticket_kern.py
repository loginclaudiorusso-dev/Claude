"""1.60: FM-Ticketnummern – jede Mail an FM zu Mängeln bekommt eine Nummer wie „FM-2026-0042“.

* Die Nummer steht im Betreff („[FM-2026-0042] FM-Auftrag: …“) und im Text – FM kann sie bei Rückfragen nennen, und
  in INNternat findet die Suche (Strg+K: „FM-42“, „FM-2026-0042“) sofort das Ticket.
* Je Standort gespeichert (``importe/modern_fm_tickets.json``), fortlaufend je Jahr. Vergeben wird beim Senden bzw.
  Öffnen in Outlook – schlägt das fehl, wird die Nummer zurückgenommen.
* Status: „erledigt“, sobald alle Mängel des Tickets behoben sind (oder von Hand erledigt), sonst „offen“.
* Rein bis auf Lesen und Schreiben der Datei (das Schreiben unter der Schreibsperre).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime

DATEI = "importe/modern_fm_tickets.json"
_NR = re.compile(r"FM-(\d{4})-(\d{1,6})", re.I)
_SUCHE = re.compile(r"(?i)\b(?:fm|ticket)[\s#:-]*(?:(\d{4})[\s-]+)?(\d{1,6})\b")


@dataclass
class Ticket:
    nr: str                                   # FM-2026-0042
    zeit: str                                 # ISO
    wer: str
    an: str
    betreff: str
    maengel: list = field(default_factory=list)   # [[Zimmer-ID, Mangelart], …]
    zimmer: list = field(default_factory=list)    # Kurzbezeichnungen für Anzeige und Suche („2-108“)
    erledigt_von_hand: str = ""               # ISO-Zeit, wenn von Hand erledigt

    @property
    def jahr_lfd(self) -> tuple[int, int]:
        m = _NR.fullmatch(self.nr)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def nummer(jahr: int, lfd: int) -> str:
    return f"FM-{jahr}-{lfd:04d}"


def naechste(tickets: list[Ticket], jahr: int) -> str:
    lfd = max((t.jahr_lfd[1] for t in tickets if t.jahr_lfd[0] == jahr), default=0)
    return nummer(jahr, lfd + 1)


def mit_nummer(nr: str, betreff: str, text: str) -> tuple[str, str]:
    """Nummer in Betreff (vorn, in Klammern) und als Zeile vor dem Gruß in den Text – nur einmal."""
    b = betreff if f"[{nr}]" in betreff else f"[{nr}] {betreff}".strip()
    if nr in text:
        return b, text
    zeile = f"Ticket: {nr} – bitte bei Rückfragen angeben."
    teile = text.rstrip("\n").split("\n")
    gruss = next((i for i in range(len(teile) - 1, -1, -1) if teile[i].strip().startswith(("Vielen Dank", "Viele Grüße"))),
                 None)
    if gruss is None:
        teile += ["", zeile]
    else:
        teile[gruss:gruss] = [zeile, ""]
    return b, "\n".join(teile) + "\n"


def offen(t: Ticket, offene: set[tuple[str, str]]) -> bool:
    """Offen, solange mindestens ein Mangel des Tickets noch offen ist und es nicht von Hand erledigt wurde."""
    if t.erledigt_von_hand:
        return False
    return any((z, a) in offene for z, a in t.maengel) if t.maengel else True


def je_mangel(tickets: list[Ticket]) -> dict[tuple[str, str], str]:
    """(Zimmer-ID, Mangelart) → neueste Ticketnummer."""
    erg: dict[tuple[str, str], str] = {}
    for t in sorted(tickets, key=lambda t: t.zeit):
        for z, a in t.maengel:
            erg[(z, a)] = t.nr
    return erg


def suchbegriff(text: str) -> tuple[int | None, int] | None:
    """„FM-42“, „fm 2026-42“, „Ticket 42“, „FM-2026-0042“ → (Jahr oder None, laufende Nummer)."""
    m = _NR.search(text or "") or _SUCHE.search(text or "")
    if not m:
        return None
    return (int(m.group(1)) if m.group(1) else None), int(m.group(2))


def finden(text: str, tickets: list[Ticket]) -> list[Ticket]:
    s = suchbegriff(text)
    if s is None:
        return []
    jahr, lfd = s
    return sorted((t for t in tickets if t.jahr_lfd[1] == lfd and (jahr is None or t.jahr_lfd[0] == jahr)),
                  key=lambda t: t.zeit, reverse=True)


# ---- Datei -----------------------------------------------------------------------------------------------------------

def laden() -> list[Ticket]:
    from belegung import speicher

    d = speicher.lesen(DATEI, {})
    roh = (d or {}).get("tickets") or [] if isinstance(d, dict) else []
    erg = []
    for x in roh:
        try:
            erg.append(Ticket(**{k: x[k] for k in Ticket.__dataclass_fields__ if k in x}))
        except Exception:                                # noqa: BLE001 – kaputte Zeile überspringen
            continue
    return erg


def _speichern(tickets: list[Ticket]) -> None:
    from belegung import speicher

    speicher.schreiben(DATEI, {"tickets": [asdict(t) for t in tickets]})


def _gesperrt(fn):
    from .kern import unter_sperre

    return unter_sperre(fn)


def anlegen(maengel: list, zimmer: list, betreff: str, an: str, wer: str = "", jetzt: datetime | None = None) -> Ticket:
    """Neue Nummer vergeben und speichern (unter der Schreibsperre – zwei PCs bekommen nie dieselbe Nummer)."""
    def tun() -> Ticket:
        alle = laden()
        j = (jetzt or datetime.now())
        t = Ticket(naechste(alle, j.year), j.isoformat(timespec="seconds"), wer, (an or "").strip(), betreff,
                   [list(m) for m in maengel], list(zimmer))
        alle.append(t)
        _speichern(alle)
        return t
    return _gesperrt(tun)()


def zuruecknehmen(nr: str) -> None:
    """Versand fehlgeschlagen – die gerade vergebene Nummer wieder entfernen."""
    def tun() -> None:
        _speichern([t for t in laden() if t.nr != nr])
    _gesperrt(tun)()


def erledigen(nr: str, an: bool = True) -> None:
    def tun() -> None:
        alle = laden()
        for t in alle:
            if t.nr == nr:
                t.erledigt_von_hand = datetime.now().isoformat(timespec="seconds") if an else ""
        _speichern(alle)
    _gesperrt(tun)()
