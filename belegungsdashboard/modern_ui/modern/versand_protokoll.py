"""1.59: Versandprotokoll – jede Mail, die das Programm verschickt oder in Outlook vorbereitet, bleibt nachvollziehbar:
wann, wer, an wen, Betreff, Anfang des Textes, über welchen Weg und mit welchem Ergebnis.

* Je Standort gespeichert (``importe/modern_versandprotokoll.json``) – alle PCs sehen dasselbe Protokoll.
* Erfasst werden: Mail an FM (einzeln und Sammelmail), Antworten und Weiterleitungen aus dem Postfach, Mails zum
  Vertragsende (Mieter). Interne Nachrichten und der Chat haben ihren eigenen Verlauf.
* Das Protokoll darf den Versand nie verhindern: Fehler beim Schreiben werden verschluckt.
* Rein bis auf Lesen und Schreiben der Datei.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime

DATEI = "importe/modern_versandprotokoll.json"
MAX_EINTRAEGE = 5000
TEXT_ANFANG = 400

ARTEN = {"fm": "Mail an FM", "antwort": "Antwort", "allen": "Allen antworten", "weiterleitung": "Weiterleitung",
         "mieter": "Mail an Mieter", "sonst": "Mail"}


@dataclass
class Eintrag:
    zeit: str                     # ISO, Sekunden
    wer: str                      # angemeldetes Konto bzw. Windows-Name
    art: str                      # Schlüssel aus ARTEN
    weg: str                      # „Outlook gesendet“ | „Outlook-Entwurf“ | „Standard-Mailprogramm“
    an: str
    betreff: str
    text: str                     # Anfang des Textes
    ergebnis: str = "ok"          # ok | Fehler: …
    von: str = ""                 # gemeinsames Postfach, falls gesetzt

    @property
    def art_text(self) -> str:
        return ARTEN.get(self.art, self.art)

    @property
    def ok(self) -> bool:
        return self.ergebnis == "ok"


def _wer() -> str:
    try:
        from . import benutzer_kern

        n = benutzer_kern.anzeige()
        if n:
            return n
    except Exception:                                  # noqa: BLE001
        pass
    try:
        from . import netz_kern

        return netz_kern.benutzer() or ""
    except Exception:                                  # noqa: BLE001
        return ""


def eintrag(art: str, weg: str, an: str, betreff: str, text: str = "", ergebnis: str = "ok", von: str = "",
            wer: str | None = None, jetzt: datetime | None = None) -> Eintrag:
    t = " ".join((text or "").split())
    return Eintrag((jetzt or datetime.now()).isoformat(timespec="seconds"), _wer() if wer is None else wer,
                   art if art in ARTEN else "sonst", weg, (an or "").strip(), (betreff or "").strip(),
                   t[:TEXT_ANFANG] + ("…" if len(t) > TEXT_ANFANG else ""), ergebnis or "ok", (von or "").strip())


def eintragen(art: str, weg: str, an: str, betreff: str, text: str = "", ergebnis: str = "ok", von: str = "") -> None:
    """Einen Versand festhalten. Schlägt das Schreiben fehl, geht der Versand trotzdem durch."""
    try:
        from belegung import speicher

        d = speicher.lesen(DATEI, {})
        liste = list((d or {}).get("eintraege") or []) if isinstance(d, dict) else []
        liste.append(asdict(eintrag(art, weg, an, betreff, text, ergebnis, von)))
        speicher.schreiben(DATEI, {"eintraege": liste[-MAX_EINTRAEGE:]})
    except Exception:                                  # noqa: BLE001 – Protokoll ist nie wichtiger als der Versand
        pass


def laden() -> list[Eintrag]:
    """Alle Einträge, neueste zuerst."""
    from belegung import speicher

    d = speicher.lesen(DATEI, {})
    roh = (d or {}).get("eintraege") or [] if isinstance(d, dict) else []
    erg = []
    for x in roh:
        try:
            erg.append(Eintrag(**{k: x.get(k, "") for k in Eintrag.__dataclass_fields__}))
        except Exception:                              # noqa: BLE001 – kaputte Zeile überspringen
            continue
    return sorted(erg, key=lambda e: e.zeit, reverse=True)


def filtern(eintraege: list[Eintrag], suche: str = "", art: str = "", nur_fehler: bool = False) -> list[Eintrag]:
    q = (suche or "").lower().strip()
    erg = []
    for e in eintraege:
        if art and e.art != art:
            continue
        if nur_fehler and e.ok:
            continue
        if q and q not in " ".join((e.an, e.betreff, e.text, e.wer, e.von)).lower():
            continue
        erg.append(e)
    return erg
