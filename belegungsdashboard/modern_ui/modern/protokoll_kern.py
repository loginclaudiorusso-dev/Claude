"""1.42: Wer hat was geändert – Protokoll je Standort für das Cockpit („Swante hat heute 5 Anreisen angelegt“).

* Jeder gespeicherte Schritt (``kern._schritt``) und jedes Rückgängig landet mit Zeit, Person und Titel in
  ``importe/modern_protokoll.json`` (höchstens 400 Einträge, 30 Tage). Geschrieben wird unter der Schreibsperre.
* Falsche oder unwichtige Einträge lassen sich für alle ausblenden („Aus der Liste“) – die Änderung selbst bleibt.
* ``ziel(titel)`` rät aus dem Titel, wo man die Änderung ansieht (Seite, Ansicht).
Rein, ohne NiceGUI.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

DATEI = "importe/modern_protokoll.json"
MAX = 400
STILL = {"Nachricht gelesen"}                          # kein Eintrag fürs Lesen
TAGE = 30


@dataclass
class Eintrag:
    id: str
    zeit: str                 # ISO, Sekunden
    wer: str
    titel: str
    aus: bool = False         # ausgeblendet („falsche Meldung“)

    @property
    def tag(self) -> date:
        return datetime.fromisoformat(self.zeit).date()

    @property
    def uhr(self) -> str:
        return self.zeit[11:16]


def _lesen() -> list[Eintrag]:
    from belegung import speicher

    try:
        d = speicher.lesen(DATEI, {}) or {}
    except Exception:                                  # noqa: BLE001 – beschädigt: leer, nicht abstürzen
        return []
    erg = []
    for x in d.get("eintraege", []) if isinstance(d, dict) else []:
        try:
            erg.append(Eintrag(**{k: x[k] for k in ("id", "zeit", "wer", "titel")}, aus=bool(x.get("aus"))))
        except (KeyError, TypeError):
            continue
    return erg


def _schreiben(es: list[Eintrag], jetzt: datetime | None = None) -> None:
    from belegung import speicher

    grenze = ((jetzt or datetime.now()) - timedelta(days=TAGE)).isoformat(timespec="seconds")
    es = [e for e in es if e.zeit >= grenze][-MAX:]
    speicher.schreiben(DATEI, {"eintraege": [asdict(e) for e in es]})


def anhaengen(titel: str, wer: str, jetzt: datetime | None = None) -> None:
    """Aufruf aus ``netz_kern.notieren`` – schon unter der Schreibsperre. Fehler werden nicht weitergereicht."""
    if not titel or titel in STILL:
        return
    jetzt = jetzt or datetime.now()
    es = _lesen()
    es.append(Eintrag(uuid.uuid4().hex[:10], jetzt.isoformat(timespec="seconds"), wer or "unbekannt", titel[:200]))
    _schreiben(es, jetzt)


def heute(tag: date | None = None, auch_aus: bool = False) -> list[Eintrag]:
    """Einträge des Tages, neueste zuerst (ohne ausgeblendete)."""
    tag = tag or date.today()
    return sorted((e for e in _lesen() if e.tag == tag and (auch_aus or not e.aus)), key=lambda e: e.zeit, reverse=True)


def je_person(es: list[Eintrag]) -> dict[str, list[Eintrag]]:
    """{Person: Einträge} – die mit den meisten Änderungen zuerst."""
    d: dict[str, list[Eintrag]] = {}
    for e in es:
        d.setdefault(e.wer, []).append(e)
    return dict(sorted(d.items(), key=lambda kv: -len(kv[1])))


def zusammenfassung(es: list[Eintrag]) -> str:
    """„Anna: 5 Änderungen · Ben: 2 Änderungen“."""
    teile = [f"{wer}: {len(x)} Änderung{'en' if len(x) != 1 else ''}" for wer, x in je_person(es).items()]
    return " · ".join(teile[:3]) + (f" · +{len(teile) - 3} weitere" if len(teile) > 3 else "")


def ausblenden(eid: str) -> str:
    from . import netz_kern

    with netz_kern.sperre():
        es = _lesen()
        e = next((x for x in es if x.id == eid), None)
        if e is None:
            raise ValueError("Diesen Eintrag gibt es nicht mehr – bitte neu laden.")
        e.aus = True
        _schreiben(es)
    return "Aus der Liste entfernt – die Änderung selbst bleibt (zurücknehmen: Strg+Z bzw. an der Stelle selbst)"


ausblenden.ohne_rueckgaengig = True

# Titel-Stichwort → (Seite, Ansicht) – wo man die Änderung ansieht
ZIELE = ((r"anreise|person|teilnehm|zuteil|zugeteilt|vorschl|zuweis|gast", ("anreisen", "personen")),
         (r"abreise", ("anreisen", "abreisen")),
         (r"reinig", ("reinigung", "liste")),
         (r"mangel|mängel|defekt|fm", ("zimmer", "maengel")),
         (r"qr", ("zimmer", "qr")),
         (r"termin|wiedervorlage|notiz", ("termine", "liste")),
         (r"mieter|mietvertrag", ("mieter", None)),
         (r"inventar|gegenstand", ("inventar", "gegenstaende")),
         (r"zimmer|sperre|umzug", ("zimmer", "uebersicht")),
         (r"nachricht", ("heute", None)),
         (r"renovier|vorhaben|budget", ("steuerung", "vorhaben")))


def ziel(titel: str) -> tuple[str, str | None]:
    t = (titel or "").lower()
    for muster, z in ZIELE:
        if re.search(muster, t):
            return z
    return ("zimmer", "aenderungen")                    # sonst: Änderungsverlauf
