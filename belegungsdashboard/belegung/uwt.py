"""UWT für Goslar: An- und Abreiselisten (PDF) und Anreisekalender (Excel).

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
# Anreisekalender (Excel): Klassen farbig, Zahl = Personen; Legende unter dem Kalender
# ---------------------------------------------------------------------------------------

_MONATE = {"januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5, "juni": 6, "juli": 7,
           "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12}
_KLASSE = re.compile(r"^\s*([A-ZÄÖÜ]{2,5}\d{2}|Sonderfall\w*)\s*$", re.I)
MAX_LUECKE_TAGE = 4   # Wochenende/Feiertag innerhalb eines Blocks – die Klasse bleibt im Haus


def _farbe(zelle) -> str | None:
    f = zelle.fill
    if not f or f.fill_type in (None, "none"):
        return None
    rgb = f.fgColor.rgb if f.fgColor is not None and f.fgColor.type == "rgb" else None
    if isinstance(rgb, str):
        return rgb[-6:].upper()
    return f"theme{f.fgColor.theme}:{round(f.fgColor.tint or 0, 2)}" if f.fgColor is not None else None


def kalender_lesen(pfad: Path) -> UwtListe:
    import openpyxl

    wb = openpyxl.load_workbook(pfad, data_only=True)
    ws = wb.active
    hinweise: list[str] = []
    jahr = None
    for zeile in ws.iter_rows(min_row=1, max_row=3):
        for c in zeile:
            if isinstance(c.value, str) and (m := re.search(r"(20\d{2})", c.value)):
                jahr = int(m.group(1))
                break
        if jahr:
            break
    if jahr is None:
        m = re.search(r"(20\d{2})", Path(pfad).stem)
        jahr = int(m.group(1)) if m else date.today().year

    # Monatsköpfe: Zeile mit Monatsnamen; Spaltenbereich bis zum nächsten Monat
    kopf_zeile, monate = None, []
    for zeile in ws.iter_rows(min_row=1, max_row=6):
        treffer = [(c.column, _MONATE[c.value.strip().lower()]) for c in zeile
                   if isinstance(c.value, str) and c.value.strip().lower() in _MONATE]
        if len(treffer) >= 1:
            kopf_zeile, monate = zeile[0].row, treffer
            break
    if not monate:
        raise ValueError("Keine Monatsnamen gefunden – ist das der UWT-Anreisekalender?")
    grenzen = [(sp, mon, (monate[i + 1][0] - 1) if i + 1 < len(monate) else ws.max_column) for i, (sp, mon) in enumerate(monate)]

    # Legende: Zellen mit Klassenname + Füllfarbe
    legende: dict[str, tuple[str, int | None]] = {}
    tage: dict[str, dict[date, int]] = {}
    for zeile in ws.iter_rows(min_row=kopf_zeile + 1):
        for c in zeile:
            if isinstance(c.value, str) and (m := _KLASSE.match(c.value)) and (fb := _farbe(c)):
                anzahl = next((x.value for x in zeile[c.column:] if isinstance(x.value, (int, float)) and _farbe(x) == fb), None)
                legende[fb] = ("Sonderfall" if m.group(1).lower().startswith("sonderfall") else m.group(1).upper(),
                               int(anzahl) if anzahl else None)
    for start, monat, ende in grenzen:
        jahr_m = jahr + 1 if monat < grenzen[0][1] else jahr   # Kalender über den Jahreswechsel
        for zeile in ws.iter_rows(min_row=kopf_zeile + 1, min_col=start, max_col=ende):
            tag_zelle = zeile[0]
            m = re.match(r"^\s*(\d{1,2})\b", str(tag_zelle.value or ""))
            if not m:
                continue
            try:
                tag = date(jahr_m, monat, int(m.group(1)))
            except ValueError:
                continue
            for c in zeile[1:]:
                if isinstance(c.value, (int, float)) and not isinstance(c.value, bool) and (fb := _farbe(c)):
                    tage.setdefault(fb, {})[tag] = int(c.value)

    bloecke: list[Block] = []
    for fb, werte in tage.items():
        if fb not in legende:
            hinweise.append(f"Farbe #{fb} ohne Eintrag in der Legende – {len(werte)} Tage übersprungen.")
            continue
        klasse, anzahl_legende = legende[fb]
        datum = sorted(werte)
        start = vorher = datum[0]
        for d in datum[1:] + [None]:
            if d is None or (d - vorher).days > MAX_LUECKE_TAGE:
                anzahl = max(werte[x] for x in werte if start <= x <= vorher)
                bloecke.append(Block(klasse, anzahl, start, vorher))
                if anzahl_legende and anzahl != anzahl_legende:
                    hinweise.append(f"{klasse} ab {start:%d.%m.}: {anzahl} Personen im Kalender, {anzahl_legende} laut Legende.")
                start = d
            vorher = d or vorher
    if not bloecke:
        raise ValueError("Im Kalender wurden keine farbigen Blöcke mit Personenzahlen gefunden.")
    return UwtListe(Path(pfad).name, sorted(bloecke, key=lambda b: (b.anreise, b.klasse)), [], hinweise)


def lesen(pfad: Path) -> UwtListe:
    """PDF-An-/Abreiseliste oder Excel-Anreisekalender."""
    return kalender_lesen(pfad) if Path(pfad).suffix.lower() in (".xlsx", ".xlsm") else pdf_lesen(pfad)


# ---------------------------------------------------------------------------------------
# Bestand: Blöcke je (Klasse, Anreise). Ein neuer Block ersetzt alle Blöcke derselben Klasse,
# die sich mit ihm überschneiden (z. B. Kalender und später die genaue PDF-Liste).
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
        alte = [k for k, x in bestand.items() if x["klasse"] == b.klasse
                and x["anreise"] <= d["abreise"] and d["anreise"] <= x["abreise"]]
        if alte:
            ersetzt += 1
            if not d["personen"]:
                d["personen"] = next((bestand[k]["personen"] for k in alte if bestand[k].get("personen")), [])
            for k in alte:
                del bestand[k]
        else:
            neu += 1
        bestand[_schluessel(d)] = d
    speicher.schreiben(DATEI, {"bloecke": sorted(bestand.values(), key=lambda b: (b["anreise"], b["klasse"]))})
    return neu, ersetzt


def block_loeschen(klasse: str, anreise: str) -> None:
    speicher.schreiben(DATEI, {"bloecke": [b for b in laden() if _schluessel(b) != f"{klasse}|{anreise}"]})


def eintraege(bloecke: list[dict]) -> list[dict]:
    return [{"kategorie": "UWT", "standort": STANDORT, "von": b["anreise"], "bis": b["abreise"],
             "anzahl": int(b["anzahl"]), "bezeichnung": f"UWT {b['klasse']}", "gruppe": f"UWT {b['klasse']}"}
            for b in bloecke]
