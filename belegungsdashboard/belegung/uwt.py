"""UWT für Goslar: An- und Abreiselisten (PDF) und Anreisekalender (Excel).

Die UWT kommt blockweise: Oben steht je Klasse die Anzahl und der Zeitraum
(„''“ = wie Zeile darüber), darunter optional die Personen mit Zimmer. Die UWT steht nicht in
der Pivot, deshalb zählt jeder Block über den ganzen Zeitraum zur Belegung (Kategorie UWT).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
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


# ---------------------------------------------------------------------------------------
# Blockbeschulungsplan der BBS (PDF): Klassen als Spalten, Wochen als Zeilen, Zeichen = Schulwoche
# ---------------------------------------------------------------------------------------

# Klassenstärken der UWTler im Internat (Stand Oktober 2026) – in der App änderbar
KLASSEN_STANDARD = {"CUA26": 15, "CUA25": 10, "CUA24": 16, "CUW26": 11, "CUW25": 9, "CUW24": 16,
                    "CUK26": 8, "CUK25": 9, "CUK24": 9}


def klassenstaerken() -> dict[str, int]:
    gespeichert = speicher.einstellungen().get("uwt_klassen", {})
    return {**KLASSEN_STANDARD, **{k: int(v) for k, v in gespeichert.items()}}


def klassenstaerken_speichern(werte: dict[str, int]) -> None:
    speicher.einstellung_setzen("uwt_klassen", {k: int(v) for k, v in werte.items()})


def _zeichen_pdf(pfad: Path) -> list[tuple[float, float, str]]:
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar

    zeichen: list[tuple[float, float, str]] = []

    def lauf(obj):
        if isinstance(obj, LTChar):
            zeichen.append((obj.x0, (obj.y0 + obj.y1) / 2, obj.get_text()))
        elif hasattr(obj, "__iter__"):
            for kind in obj:
                lauf(kind)

    for seite in extract_pages(str(pfad), maxpages=1):
        lauf(seite)
    return zeichen


def _woerter(zeichen: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    """Zeichen zu Wörtern je Zeile zusammenfassen: (x-Mitte, y, Text)."""
    zeilen: dict[int, list] = {}
    for x, y, t in zeichen:
        zeilen.setdefault(round(y / 2), []).append((x, y, t))
    woerter = []
    for zs in zeilen.values():
        zs.sort()
        akt: list = []
        for z in zs:
            if akt and (z[0] - akt[-1][0] > 7 or not z[2].strip()):
                woerter.append(akt)
                akt = []
            if z[2].strip():
                akt.append(z)
        if akt:
            woerter.append(akt)
    return [((w[0][0] + w[-1][0]) / 2 + 2, w[0][1], "".join(z[2] for z in w)) for w in woerter]


def blockplan_parse(zeichen: list[tuple[float, float, str]], datei: str = "",
                    staerken: dict[str, int] | None = None) -> UwtListe:
    staerken = klassenstaerken() if staerken is None else staerken
    woerter = _woerter(zeichen)
    kurz = [w for w in woerter if re.fullmatch(r"CU[AWK]|CC[K]", w[2])]
    if len(kurz) < 3:
        raise ValueError("Keine Klassenspalten (CUA/CUW/CUK) gefunden – ist das der Blockbeschulungsplan?")
    kopf_y = max(set(round(w[1]) for w in kurz), key=lambda y: sum(1 for w in kurz if round(w[1]) == y))
    kurz = [w for w in kurz if abs(w[1] - kopf_y) < 2]
    jahrgaenge = [w for w in woerter if re.fullmatch(r"\d{2}", w[2]) and 5 < kopf_y - w[1] < 20]
    spalten = []
    for x, _y, name in sorted(kurz):
        jg = min(jahrgaenge, key=lambda w: abs(w[0] - x), default=None)
        if jg is None or abs(jg[0] - x) > 8:
            continue
        spalten.append((x, f"{name}{jg[2]}"))
    text = " ".join(w[2] for w in woerter)
    m = re.search(r"(20\d{2})\s*/\s*(20\d{2})", text)
    jahr1 = int(m.group(1)) if m else date.today().year
    abstand = min(b[0] - a[0] for a, b in zip(spalten, spalten[1:])) if len(spalten) > 1 else 18

    # Zeilen: erstes Datum links = Montag; Zeichen in einer Klassenspalte = Schulwoche
    zeilen: dict[int, list] = {}
    for w in woerter:
        zeilen.setdefault(round(w[1]), []).append(w)
    wochen: dict[str, set[date]] = {name: set() for _x, name in spalten}
    for y, ws in zeilen.items():
        if y >= kopf_y - 5:
            continue
        daten = sorted((w for w in ws if re.fullmatch(r"\d{1,2}\.\d{1,2}\.?", w[2])), key=lambda w: w[0])
        if not daten:
            continue
        t, mo = (int(x) for x in daten[0][2].rstrip(".").split("."))
        try:
            montag = date(jahr1 if mo >= 8 else jahr1 + 1, mo, t)
        except ValueError:
            continue
        rechts = daten[-1][0]
        for x, _y, zeichen_text in ws:
            if x <= rechts + 5 or re.fullmatch(r"\d+|\d{1,2}\.\d{1,2}\.?", zeichen_text):
                continue
            sp = min(spalten, key=lambda s: abs(s[0] - x))
            if abs(sp[0] - x) <= abstand / 2:
                wochen[sp[1]].add(montag)

    bloecke, hinweise = [], []
    for klasse, montage in wochen.items():
        if not montage:
            continue
        anzahl = int(staerken.get(klasse, 0))
        folge = sorted(montage)
        start = vorher = folge[0]
        for d in folge[1:] + [None]:
            if d is None or (d - vorher).days != 7:
                bloecke.append(Block(klasse, anzahl, start, vorher + timedelta(days=4)))
                start = d
            vorher = d or vorher
    ohne = sorted({b.klasse for b in bloecke if b.anzahl <= 0})
    if ohne:
        hinweise.append("Ohne Klassenstärke (zählen nicht, z. B. Chemikanten ohne Internat): " + ", ".join(ohne))
    if not bloecke:
        raise ValueError("Im Plan wurden keine Schulwochen erkannt.")
    return UwtListe(datei, sorted(bloecke, key=lambda b: (b.anreise, b.klasse)), [], hinweise)


def blockplan_lesen(pfad: Path, staerken: dict[str, int] | None = None) -> UwtListe:
    try:
        zeichen = _zeichen_pdf(Path(pfad))
    except ImportError as exc:  # pragma: no cover
        raise ValueError("Zum Lesen des Blockplans wird das Paket „pdfminer.six“ benötigt (pip install pdfminer.six).") from exc
    return blockplan_parse(zeichen, Path(pfad).name, staerken)


def ist_blockplan(pfad: Path) -> bool:
    try:
        from pypdf import PdfReader

        text = PdfReader(str(pfad)).pages[0].extract_text() or ""
    except Exception:
        return False
    return "blockbeschulung" in text.lower() or "schuljahr" in text.lower()


def lesen(pfad: Path) -> UwtListe:
    """Excel-Anreisekalender, Blockbeschulungsplan (PDF) oder An-/Abreiseliste eines Blocks (PDF)."""
    pfad = Path(pfad)
    if pfad.suffix.lower() in (".xlsx", ".xlsm"):
        return kalender_lesen(pfad)
    if ist_blockplan(pfad):
        return blockplan_lesen(pfad)
    return pdf_lesen(pfad)


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
        if b.anzahl <= 0:
            continue    # Klasse ohne Internat (z. B. Chemikanten)
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


# ---------------------------------------------------------------------------------------
# Eingangsordner „UWT“: Blockbeschulungsplan, Anreisekalender oder Listen dort ablegen –
# beim Start bzw. Öffnen des Zimmerplans werden neue/geänderte Dateien übernommen.
# ---------------------------------------------------------------------------------------

EINGANG = "UWT"
_KENNUNGEN = f"{speicher.IMPORT_ORDNER}/uwt_eingang.json"


def eingangsordner() -> Path:
    return speicher.pfad(EINGANG)


def automatisch_importieren(ordner: Path | None = None) -> list[str]:
    """Liest alle neuen oder geänderten PDF/Excel-Dateien im Ordner „UWT“ ein (älteste zuerst, damit die
    neueste gewinnt) – Blockpläne, Kalender, Listen und die Klassenübersicht. Gibt je Datei eine Meldung zurück."""
    ordner = ordner or eingangsordner()
    if not ordner.is_dir():
        return []
    dateien = sorted((p for p in ordner.iterdir() if p.suffix.lower() in (".pdf", ".xlsx", ".xlsm")
                      and not p.name.startswith("~$")), key=lambda p: p.stat().st_mtime)
    bekannt = speicher.lesen(_KENNUNGEN, {})
    ergebnis = []
    for p in dateien:
        kennung = int(p.stat().st_mtime)
        if bekannt.get(p.name) == kennung:
            continue
        try:
            if ist_klassenliste(p):
                klassen, hinweise = klassen_lesen(p)
                klassen_importieren(klassen, p.name, hinweise)
                n = sum(len(v) for v in klassen.values())
                ergebnis.append(f"{p.name} ({len(klassen)} Klassen, {n} Personen, "
                                f"{sum(1 for v in klassen.values() for x in v if x.partner)} mit DZ-Partner)")
            else:
                neu, ersetzt = importieren(lesen(p))
                ergebnis.append(f"{p.name} ({neu} Blöcke neu, {ersetzt} aktualisiert)")
        except Exception:
            continue
        bekannt[p.name] = kennung
    if ergebnis:
        speicher.schreiben(_KENNUNGEN, bekannt)
    return ergebnis


# ---------------------------------------------------------------------------------------
# Klassenübersicht (Excel, ein Blatt je Klasse): Teilnehmende mit „DZ Partner“ – gleiche Nummer =
# gemeinsames Doppelzimmer, „-“ = allein. Alles unter „STORNO“ zählt nicht mehr.
# ---------------------------------------------------------------------------------------

KLASSEN_DATEI = f"{speicher.IMPORT_ORDNER}/uwt_klassen.json"
_KLASSE = re.compile(r"^[A-ZÄÖÜ]{2,5}\d{2}$")


@dataclass
class KlassenPerson:
    tn_id: str
    name: str            # „Nachname, Vorname“
    geschlecht: str      # "w" bei „(w)“ im Vornamen, sonst ""
    dz: str              # "" = Klasse ohne DZ-Liste | "allein" | "<Klasse>:<Nr>" = DZ-Gruppe
    bemerkung: str = ""

    @property
    def partner(self) -> bool:
        return self.dz not in ("", "allein")


def _kopf(zeile: tuple) -> dict[str, int] | None:
    texte = [str(c).strip().lower() if c is not None else "" for c in zeile]
    if "id" not in texte or "name" not in texte:
        return None
    spalten = {t: i for i, t in enumerate(texte) if t}
    return {k: spalten[t] for k, t in (("id", "id"), ("name", "name"), ("vorname", "vorname"),
                                         ("dz", "dz partner"), ("bemerkung", "bemerkung")) if t in spalten}


def ist_klassenliste(pfad: Path) -> bool:
    if Path(pfad).suffix.lower() not in (".xlsx", ".xlsm"):
        return False
    from openpyxl import load_workbook

    wb = load_workbook(pfad, read_only=True, data_only=True)
    try:
        for ws in wb.worksheets:
            for zeile in ws.iter_rows(max_row=6, values_only=True):
                k = _kopf(zeile)
                if k and "dz" in k:
                    return True
        return False
    finally:
        wb.close()


def klassen_lesen(pfad: Path) -> tuple[dict[str, list[KlassenPerson]], list[str]]:
    """Klassen → aktive Teilnehmende; dazu Hinweise (DZ-Gruppen, die nicht genau zwei Personen haben)."""
    from openpyxl import load_workbook

    wb = load_workbook(pfad, read_only=True, data_only=True)
    klassen: dict[str, list[KlassenPerson]] = {}
    hinweise: list[str] = []
    try:
        for ws in wb.worksheets:
            klasse = ws.title.strip().upper().replace(" ", "")
            if not _KLASSE.match(klasse):
                continue
            kopf = None
            roh: list[tuple[str, str, str, str, str]] = []
            for zeile in ws.iter_rows(values_only=True):
                if kopf is None:
                    kopf = _kopf(zeile)
                    continue
                texte = [str(c).strip() for c in zeile if c is not None]
                if any(t.upper().startswith(("STORNO", "ANMERKUNG")) for t in texte):
                    break
                wert = lambda k: zeile[kopf[k]] if k in kopf and kopf[k] < len(zeile) else None
                tn, name = wert("id"), wert("name")
                if tn is None or not name or not re.fullmatch(r"\d+(\.0)?", str(tn).strip()):
                    continue
                vorname = str(wert("vorname") or "").strip()
                geschlecht = "w" if re.search(r"\(\s*w\s*\)", vorname) else "m" if re.search(r"\(\s*m\s*\)", vorname) else ""
                vorname = re.sub(r"\s*\([wmd]\)\s*", " ", vorname).strip()
                dz = wert("dz")
                roh.append((str(int(float(tn))), f"{str(name).strip()}, {vorname}" if vorname else str(name).strip(),
                            geschlecht, "" if dz is None else str(dz).strip(), str(wert("bemerkung") or "").strip()))
            if not roh:
                continue
            mit_liste = any(d for *_x, d, _b in roh)
            gruppen: dict[str, list[str]] = {}
            for tn, name, _g, d, _b in roh:
                m = re.match(r"^(\d+)", d)
                if m:
                    gruppen.setdefault(m.group(1), []).append(name)
            personen = []
            for tn, name, g, d, bem in roh:
                m = re.match(r"^(\d+)", d)
                if not mit_liste:
                    dz = ""
                elif m and len(gruppen[m.group(1)]) >= 2:
                    dz = f"{klasse}:{m.group(1)}"
                else:
                    dz = "allein"
                personen.append(KlassenPerson(tn, name, g, dz, bem))
            for nr, namen in sorted(gruppen.items()):
                if len(namen) == 1:
                    hinweise.append(f"{klasse}: DZ-Partner von {namen[0]} fehlt (storniert?) – wohnt allein.")
                elif len(namen) > 2:
                    hinweise.append(f"{klasse}: DZ-Nr. {nr} hat {len(namen)} Personen ({'; '.join(namen)}) – "
                                    "nur zwei passen in ein Doppelzimmer, bitte klären.")
            if not mit_liste:
                hinweise.append(f"{klasse}: noch keine DZ-Liste – Doppelzimmer werden innerhalb der Klasse vorgeschlagen.")
            klassen[klasse] = personen
    finally:
        wb.close()
    return klassen, hinweise


def klassen_importieren(klassen: dict[str, list[KlassenPerson]], datei: str = "", hinweise: list[str] | None = None) -> None:
    """Speichert die Klassen (ersetzt nur die enthaltenen) und setzt die Klassenstärke auf die Zahl der
    Teilnehmenden – kommende Blöcke ohne Namensliste übernehmen sie."""
    from dataclasses import asdict

    roh = speicher.lesen(KLASSEN_DATEI, {})
    alle = roh.get("klassen", {})
    for k, personen in klassen.items():
        alle[k] = [asdict(p) for p in personen]
    speicher.schreiben(KLASSEN_DATEI, {"klassen": alle, "datei": datei, "hinweise": hinweise or [],
                                       "importiert_am": datetime.now().isoformat(timespec="seconds")})
    klassenstaerken_speichern({**klassenstaerken(), **{k: len(v) for k, v in klassen.items()}})
    heute = date.today().isoformat()
    bloecke = laden()
    for b in bloecke:
        if b["klasse"] in klassen and b["abreise"] >= heute and not b.get("personen"):
            b["anzahl"] = len(klassen[b["klasse"]])
    speicher.schreiben(DATEI, {"bloecke": bloecke})


def klassen_laden() -> dict[str, list[dict]]:
    return speicher.lesen(KLASSEN_DATEI, {}).get("klassen", {})


def klassen_info() -> dict:
    """Datei, Importzeit und Hinweise der zuletzt übernommenen Klassenübersicht."""
    roh = speicher.lesen(KLASSEN_DATEI, {})
    return {k: roh.get(k) for k in ("datei", "importiert_am", "hinweise")}
