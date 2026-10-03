"""UWT-An- und Abreiselisten (PDF) für Goslar.

Die UWT kommt blockweise: Oben steht je Klasse die Anzahl und der Zeitraum
(„''“ = wie Zeile darüber), darunter optional die Personen mit Zimmer. Die UWT steht nicht in
der Pivot, deshalb zählt jeder Block über den ganzen Zeitraum zur Belegung (Kategorie UWT).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from . import speicher

STANDORT = "BFW GS"
DATEI = f"{speicher.IMPORT_ORDNER}/uwt.json"

_DATUM = r"\d{1,2}\.\d{1,2}\.\d{2,4}"
_WIE_OBEN = r"(?:''|\"|„|“|”|″|-\s*\"\s*-)"
_KLASSE_ZEILE = re.compile(rf"^\s*(\d{{1,3}})\s+([A-ZÄÖÜ]{{2,5}}\d{{2}})\s+({_DATUM}|{_WIE_OBEN})\s+({_DATUM}|{_WIE_OBEN})", re.M)
_PERSON = re.compile(r"(?<!\d)(\d{5,7})\s+(.+?)\s+([A-ZÄÖÜ]{2,5}\d{2})\s+(\d(?:\.\d)?-\d{3,4}(?:/\d)?)", re.S)


@dataclass
class Block:
    klasse: str
    anzahl: int
    anreise: date
    abreise: date


@dataclass
class UwtPerson:
    tn_id: str
    name: str
    klasse: str
    zimmer: str


@dataclass
class UwtListe:
    datei: str
    bloecke: list[Block]
    personen: list[UwtPerson] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)


def _datum(text: str) -> date:
    t, m, j = (int(x) for x in text.split("."))
    return date(j + 2000 if j < 100 else j, m, t)


def parse(text: str, layout: str = "", datei: str = "") -> UwtListe:
    """Text aus dem PDF -> Blöcke und Personen. ``layout`` (spaltentreuer Text) dient nur
    dazu, Nachname und Vorname sauber zu trennen."""
    bloecke, hinweise = [], []
    vorher: tuple[date | None, date | None] = (None, None)
    for m in _KLASSE_ZEILE.finditer(text):
        anzahl, klasse, an, ab = m.groups()
        try:
            anreise = _datum(an) if re.match(_DATUM, an) else vorher[0]
            abreise = _datum(ab) if re.match(_DATUM, ab) else vorher[1]
        except ValueError:
            hinweise.append(f"{klasse}: Datum nicht lesbar – übersprungen.")
            continue
        if anreise is None or abreise is None:
            hinweise.append(f"{klasse}: kein Zeitraum („''“ ohne Zeile darüber) – übersprungen.")
            continue
        if abreise < anreise:
            hinweise.append(f"{klasse}: Abreise vor Anreise – übersprungen.")
            continue
        vorher = (anreise, abreise)
        bloecke.append(Block(klasse, int(anzahl), anreise, abreise))
    if not bloecke:
        raise ValueError("Keine Klassen mit Anzahl und Zeitraum gefunden – ist das eine UWT-An- und Abreiseliste?")

    namen: dict[str, str] = {}
    for zeile in layout.splitlines():
        teile = [t for t in re.split(r"\s{2,}", zeile.strip()) if t]
        for i, t in enumerate(teile):
            if re.fullmatch(r"\d{5,7}", t) and i + 1 < len(teile):
                nachname = teile[i + 1]
                vorname = teile[i + 2] if i + 2 < len(teile) and not re.fullmatch(r"[A-ZÄÖÜ]{2,5}\d{2}", teile[i + 2]) else ""
                namen[t] = f"{nachname}, {vorname}" if vorname else nachname
    personen, gesehen = [], set()
    for m in _PERSON.finditer(text):
        tn_id, name, klasse, zimmer = m.groups()
        if tn_id in gesehen:
            continue
        gesehen.add(tn_id)
        name = namen.get(tn_id) or " ".join(name.split())
        personen.append(UwtPerson(tn_id, name, klasse, zimmer))
    return UwtListe(datei, bloecke, personen, hinweise)


def pdf_lesen(pfad: Path) -> UwtListe:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ValueError("Zum Lesen von PDFs wird das Paket „pypdf“ benötigt (pip install pypdf).") from exc
    leser = PdfReader(str(pfad))
    text = "\n".join(s.extract_text() or "" for s in leser.pages)
    try:
        layout = "\n".join(s.extract_text(extraction_mode="layout") or "" for s in leser.pages)
    except Exception:
        layout = ""
    if not text.strip():
        raise ValueError("Das PDF enthält keinen lesbaren Text (eingescannt?).")
    return parse(text, layout, Path(pfad).name)


# ---------------------------------------------------------------------------------------
# Bestand: Blöcke je (Klasse, Anreise); ein neuer Upload desselben Blocks ersetzt ihn.
# ---------------------------------------------------------------------------------------

def _schluessel(b: dict) -> str:
    return f"{b['klasse']}|{b['anreise']}"


def laden() -> list[dict]:
    return list(speicher.lesen(DATEI, {}).get("bloecke", []))


def importieren(liste: UwtListe) -> tuple[int, int]:
    bestand = {_schluessel(b): b for b in laden()}
    neu = ersetzt = 0
    zeit = datetime.now().isoformat(timespec="seconds")
    for b in liste.bloecke:
        d = {"klasse": b.klasse, "anzahl": b.anzahl, "anreise": b.anreise.isoformat(), "abreise": b.abreise.isoformat(),
             "datei": liste.datei, "importiert_am": zeit,
             "personen": [{"tn_id": p.tn_id, "name": p.name, "zimmer": p.zimmer}
                          for p in liste.personen if p.klasse == b.klasse]}
        k = _schluessel(d)
        if k in bestand:
            ersetzt += 1
            if not d["personen"]:
                d["personen"] = bestand[k].get("personen", [])
        else:
            neu += 1
        bestand[k] = d
    speicher.schreiben(DATEI, {"bloecke": sorted(bestand.values(), key=lambda b: (b["anreise"], b["klasse"]))})
    return neu, ersetzt


def block_loeschen(klasse: str, anreise: str) -> None:
    speicher.schreiben(DATEI, {"bloecke": [b for b in laden() if _schluessel(b) != f"{klasse}|{anreise}"]})


def eintraege(bloecke: list[dict]) -> list[dict]:
    return [{"kategorie": "UWT", "standort": STANDORT, "von": b["anreise"], "bis": b["abreise"],
             "anzahl": int(b["anzahl"]), "bezeichnung": f"UWT {b['klasse']}", "gruppe": f"UWT {b['klasse']}"}
            for b in bloecke]
