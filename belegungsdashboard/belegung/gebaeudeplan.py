"""Gebäudeplan Goslar (Word-Export) einlesen: Zimmer, Betten, Belegungen und Sperrungen.

Aufbau des Exports (je Zimmer untereinander):
    GS-2-109                     Zimmer-ID
    1 Bett | 2 Betten
    Werner, Jessica (GS ASS PS 260909)      je Bett: Name (Maßnahme) …
    09.09.2026 - 20.10.2026                 … Zeitraum
    Belegt                                  … Status
    -- oder --
    Frei | Reno offen / 16.09.2026 - 31.12.2026 / Gesperrt | Renoviert
    -- oder --
    Frei teilw. / Name (Maßnahme) / Zeitraum / Zimmerfreigabe von - bis / Belegt

„Zimmerfreigabe“ heißt: Das Zimmer ist vergeben, steht im Freigabe-Zeitraum aber zur
Verfügung (z. B. Praktikum). Die Belegung wird deshalb um diesen Zeitraum ausgespart.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from . import speicher

DATEI = f"{speicher.IMPORT_ORDNER}/gebaeudeplan.json"

_ZIMMER = re.compile(r"^GS-([\d.]+)-([A-Z]?\d+)$")
_HAUS = re.compile(r"^GS-Haus-([\d.]+)$")
_ETAGE = re.compile(r"^(\d{1,2})\.\s*Etage$")
_ZEITRAUM = re.compile(r"^(\d{1,2}\.\d{1,2}\.\d{4})\s*-\s*(\d{1,2}\.\d{1,2}\.\d{4})$")
_FREIGABE = re.compile(r"Zimmerfreigabe\s+(\d{1,2}\.\d{1,2}\.\d{4})\s*-\s*(\d{1,2}\.\d{1,2}\.\d{4})")
_PERSON = re.compile(r"^(.+?)\s*\(([^()]*)\)$")
_BETTEN = re.compile(r"^(\d+)\s*Bett(en)?$")


@dataclass
class Belegung:
    zimmer: str
    von: date
    bis: date
    art: str                 # belegt | gesperrt | geplant
    name: str = ""
    massnahme: str = ""
    grund: str = ""          # bei Sperrung: Renoviert, Reno offen, Mieter …
    person: str = ""         # Schlüssel der Anreise-Person (bei geplant)

    def zu_dict(self) -> dict:
        d = asdict(self)
        d["von"], d["bis"] = self.von.isoformat(), self.bis.isoformat()
        return d

    @staticmethod
    def aus_dict(d: dict) -> "Belegung":
        return Belegung(**{**d, "von": date.fromisoformat(d["von"]), "bis": date.fromisoformat(d["bis"])})

    def ueberschneidet(self, von: date, bis: date, puffer: int = 0) -> bool:
        """Zeitraum [von, bis] kollidiert, wenn er nicht mindestens ``puffer`` Tage Abstand hält."""
        return von <= self.bis + timedelta(days=puffer) and self.von <= bis + timedelta(days=puffer)


@dataclass
class PlanZimmer:
    id: str
    haus: str
    etage: str          # "1" … "10", "E" (Erdgeschoss), "U" (Untergeschoss)
    nr: str
    betten: int


@dataclass
class Gebaeudeplan:
    datei: str
    stand: date | None
    zimmer: list[PlanZimmer]
    belegungen: list[Belegung]
    hinweise: list[str] = field(default_factory=list)


def _d(text: str) -> date:
    return datetime.strptime(text, "%d.%m.%Y").date()


def _zeilen_docx(pfad: Path) -> tuple[list[str], date | None]:
    with zipfile.ZipFile(pfad) as z:
        xml = z.read("word/document.xml").decode("utf-8")
        try:
            kern = z.read("docProps/core.xml").decode("utf-8")
            m = re.search(r"<dcterms:modified[^>]*>(\d{4}-\d{2}-\d{2})", kern)
            stand = date.fromisoformat(m.group(1)) if m else None
        except KeyError:
            stand = None
    xml = re.sub(r"<w:tab/>", "\t", xml)
    xml = re.sub(r"<w:br/>|</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    for alt, neu in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(alt, neu)
    return [z.strip() for z in text.splitlines() if z.strip()], stand


def parse_zeilen(zeilen: list[str], datei: str = "", stand: date | None = None) -> Gebaeudeplan:
    zimmer: list[PlanZimmer] = []
    belegungen: list[Belegung] = []
    hinweise: list[str] = []
    haus = etage = None
    i = 0
    gesehen: set[str] = set()

    while i < len(zeilen):
        z = zeilen[i]
        if m := _HAUS.match(z):
            haus = m.group(1)
            i += 1
            continue
        if m := _ETAGE.match(z):
            etage = str(int(m.group(1)))
            i += 1
            continue
        if z.lower().startswith("erdgescho"):
            etage = "E"
            i += 1
            continue
        if z.lower().startswith("untergescho"):
            etage = "U"
            i += 1
            continue
        m = _ZIMMER.match(z)
        if not m:
            i += 1
            continue
        zid, nr = z, m.group(2)
        # Block bis zum nächsten Zimmer / Haus / Etage einsammeln
        j = i + 1
        block = []
        while j < len(zeilen) and not (_ZIMMER.match(zeilen[j]) or _HAUS.match(zeilen[j]) or _ETAGE.match(zeilen[j])
                                       or zeilen[j].lower().startswith(("erdgescho", "untergescho"))):
            block.append(zeilen[j])
            j += 1
        i = j
        betten = 1
        if block and (mb := _BETTEN.match(block[0])):
            betten = int(mb.group(1))
            block = block[1:]
        if zid in gesehen:
            hinweise.append(f"{zid} steht doppelt im Plan – der zweite Eintrag wird ignoriert.")
            continue
        gesehen.add(zid)
        zimmer.append(PlanZimmer(zid, haus or m.group(1), etage or "?", nr, betten))
        belegungen += _block_auswerten(zid, block, hinweise)
    return Gebaeudeplan(datei, stand, zimmer, belegungen, hinweise)


def _block_auswerten(zid: str, block: list[str], hinweise: list[str]) -> list[Belegung]:
    ergebnis: list[Belegung] = []
    freigaben: list[tuple[date, date]] = []
    text_davor: list[str] = []
    k = 0
    while k < len(block):
        z = block[k]
        if mf := _FREIGABE.search(z):
            freigaben.append((_d(mf.group(1)), _d(mf.group(2))))
            k += 1
            continue
        if mz := _ZEITRAUM.match(z):
            von, bis = _d(mz.group(1)), _d(mz.group(2))
            k += 1
            while k < len(block) and (mf := _FREIGABE.search(block[k])):
                freigaben.append((_d(mf.group(1)), _d(mf.group(2))))
                k += 1
            status = block[k] if k < len(block) else ""
            beschreibung = " ".join(t for t in text_davor if t not in ("Frei", "Frei teilw."))
            text_davor = []
            mp = _PERSON.match(beschreibung)
            if status.lower().startswith("belegt") and mp:
                massnahme = mp.group(2).strip()
                ergebnis.append(Belegung(zid, von, bis, "belegt", mp.group(1).strip(),
                                         "" if massnahme.lower() == "null" else massnahme))
            elif status.lower().startswith("belegt"):
                ergebnis.append(Belegung(zid, von, bis, "belegt", beschreibung))
            else:
                grund = status or "Gesperrt"
                if re.search(r"mieter", beschreibung, re.I):
                    ergebnis.append(Belegung(zid, von, bis, "belegt", beschreibung, "Miete", grund))
                else:
                    ergebnis.append(Belegung(zid, von, bis, "gesperrt", "", "", f"{grund}: {beschreibung}".strip(": ")))
            k += 1
            continue
        text_davor.append(z)
        k += 1

    # Zimmerfreigaben: Belegungen um den Freigabe-Zeitraum kürzen bzw. teilen
    for f_von, f_bis in freigaben:
        neu = []
        for b in ergebnis:
            if b.art != "belegt" or not b.ueberschneidet(f_von, f_bis):
                neu.append(b)
                continue
            if b.von < f_von:
                neu.append(Belegung(**{**asdict(b), "bis": f_von - timedelta(days=1)}))
            if b.bis > f_bis:
                neu.append(Belegung(**{**asdict(b), "von": f_bis + timedelta(days=1)}))
        ergebnis = neu
    return ergebnis


def lesen(pfad: Path) -> Gebaeudeplan:
    pfad = Path(pfad)
    if pfad.suffix.lower() != ".docx":
        raise ValueError("Bitte den Gebäudeplan als Word-Datei (.docx) wählen.")
    zeilen, stand = _zeilen_docx(pfad)
    plan = parse_zeilen(zeilen, pfad.name, stand)
    if not plan.zimmer:
        raise ValueError("Im Dokument wurden keine Zimmer (GS-Haus-…/GS-…-…) gefunden – ist das der Gebäudeplan?")
    return plan


# ---------------------------------------------------------------------------------------
# Ablage
# ---------------------------------------------------------------------------------------

def speichern(plan: Gebaeudeplan) -> None:
    speicher.schreiben(DATEI, {
        "datei": plan.datei, "stand": plan.stand.isoformat() if plan.stand else None,
        "importiert_am": datetime.now().isoformat(timespec="seconds"),
        "zimmer": [asdict(z) for z in plan.zimmer],
        "belegungen": [b.zu_dict() for b in plan.belegungen],
        "hinweise": plan.hinweise,
    })


def laden() -> tuple[Gebaeudeplan | None, dict]:
    roh = speicher.lesen(DATEI, None)
    if not roh:
        return None, {}
    plan = Gebaeudeplan(
        roh.get("datei", ""), date.fromisoformat(roh["stand"]) if roh.get("stand") else None,
        [PlanZimmer(**z) for z in roh.get("zimmer", [])],
        [Belegung.aus_dict(b) for b in roh.get("belegungen", [])], roh.get("hinweise", []),
    )
    return plan, {"importiert_am": roh.get("importiert_am")}
