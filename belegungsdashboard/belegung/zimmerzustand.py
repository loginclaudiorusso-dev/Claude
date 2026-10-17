"""Zimmerzustand einmalig übernehmen (z. B. aus der ZKL): Renovierung, Boden und Mängel – nach dem festen Standard.

Datei ``Zimmerzustand_Import.tsv`` (Tabulator), je Zeile ein Befund::

    Zimmer   Art     Wert              Datum        Notiz
    2-115    reno    2026-08                        (Jahr-Monat oder Datum)
    2-115    boden   PVC                            (ein Boden aus zimmerliste.BOEDEN)
    2-102    mangel  wand              2026-03-17   Teilstreichen – weiße Flecken

Regeln wie bei der Renovierungsliste und den Mängeln: das neuere Renovierungsdatum gewinnt; ein genannter Boden gilt
als sicher und ersetzt nur einen fehlenden oder vermuteten; ein Mangel wird nur geöffnet, wenn dieselbe Art im Zimmer
nicht schon offen ist. Nichts wird gelöscht. Rein, ohne Qt.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date

from . import maengel, protokoll, speicher
from . import zimmerplan as zp

IMPORT_DATEI = "Zimmerzustand_Import.tsv"   # liegt sie im Programm- oder Datenordner, wird sie einmal übernommen
_MONAT = re.compile(r"^(\d{4})-(\d{2})$")
GLEICHE_RENO_MONATE = 2     # Monatsangabe bis 2 Monate nach einem genauen Datum = dieselbe Renovierung


@dataclass
class Befund:
    zimmer: str
    art: str            # reno | boden | mangel
    wert: str
    datum: date | None = None
    notiz: str = ""


@dataclass
class Ergebnis:
    reno: int = 0
    boden: int = 0
    maengel: int = 0
    boden_abweichend: list[str] = field(default_factory=list)   # „2-101: Teppich (ZKL: PVC)“ – sicher eingetragen, nicht geändert
    fehler: list[str] = field(default_factory=list)              # Zeilen ohne Zimmer oder mit unbekanntem Wert

    def text(self) -> str:
        teile = [f"{self.reno} Renovierungen", f"{self.boden} Böden", f"{self.maengel} Mängel"]
        if self.boden_abweichend:
            teile.append(f"{len(self.boden_abweichend)} Böden abweichend (nicht geändert)")
        if self.fehler:
            teile.append(f"{len(self.fehler)} Zeilen ohne Zimmer")
        return " · ".join(teile)


def _reno_wert(wert: str) -> str | None:
    """„2026-08“ (Monat) oder „2026-08-15“ (Tag) – sonst None."""
    if _MONAT.match(wert):
        return wert if 1 <= int(wert[5:]) <= 12 else None
    try:
        return date.fromisoformat(wert).isoformat()
    except ValueError:
        return None


def _monate(iso: str) -> int:
    return int(iso[:4]) * 12 + int(iso[5:7])


def lesen(text: str, bekannt: set[str]) -> tuple[list[Befund], list[str]]:
    from .zimmerliste import BOEDEN
    from .zkl import zimmer_id

    erg, fehler = [], []
    for zeile in (text or "").splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        teile = [t.strip() for t in zeile.split("\t")] + [""] * 5
        roh, art, wert, datum, notiz = teile[:5]
        zid = zimmer_id(roh, bekannt)
        try:
            tag = date.fromisoformat(datum) if datum else None
        except ValueError:
            tag = None
        gueltig = {"reno": _reno_wert(wert) is not None, "boden": wert in BOEDEN,
                   "mangel": wert in maengel.NAMEN}.get(art.lower(), False)
        if zid is None or zid not in bekannt or not gueltig:
            fehler.append(zeile.strip())
            continue
        erg.append(Befund(zid, art.lower(), wert, tag, notiz))
    return erg, fehler


def anwenden(stand: zp.Planstand, befunde: list[Befund], heute: date | None = None) -> Ergebnis:
    """Befunde übernehmen; speichert Stammdaten und Mängel. Gibt die Zahl der Änderungen je Art zurück."""
    heute = heute or date.today()
    erg = Ergebnis()
    zimmer = {z.id: z for z in stand.zimmer}
    for b in befunde:
        z = zimmer[b.zimmer]
        if b.art == "reno":
            neu = _reno_wert(b.wert)
            alt = z.renoviert if z.renoviert and z.renoviert[:1].isdigit() else ""
            if alt and len(alt) == 10 and len(neu) == 7 and 0 <= _monate(neu) - _monate(alt) <= GLEICHE_RENO_MONATE:
                continue                                          # genaues Datum behalten
            if neu[:len(alt)] > alt[:len(neu)] or not alt:       # Monat und Tag vergleichbar: das neuere gewinnt
                z.renoviert = neu
                erg.reno += 1
        elif b.art == "boden":
            if not z.boden or z.boden_vermutet:
                if (z.boden, z.boden_vermutet) != (b.wert, False):
                    z.boden, z.boden_vermutet = b.wert, False
                    erg.boden += 1
            elif z.boden != b.wert:
                erg.boden_abweichend.append(f"{z.kurz}: {z.boden} (Quelle: {b.wert})")
    if erg.reno or erg.boden:
        zp.stammdaten_speichern(stand.zimmer, stand.plan)

    alle = maengel.laden()
    offen = {(m.zimmer, m.art) for m in alle if m.behoben is None}
    neu_m = []
    for b in befunde:
        if b.art == "mangel" and (b.zimmer, b.wert) not in offen:
            offen.add((b.zimmer, b.wert))
            neu_m.append(maengel.Mangel(b.zimmer, b.wert, b.datum or heute, None, b.notiz))
    if neu_m:
        speicher.schreiben(maengel.DATEI, {"maengel": [m.zu_dict() for m in alle + neu_m]})
        protokoll.eintragen([{"aktion": "Mangel gemeldet", "name": m.text, "person": "", "alt": "", "neu": m.zimmer,
                              "von": m.seit.isoformat(), "quelle": "Zimmerzustand-Import"} for m in neu_m])
    erg.maengel = len(neu_m)
    return erg


def auto_import(stand: zp.Planstand) -> Ergebnis | None:
    """Einmalig ``Zimmerzustand_Import.tsv`` aus Daten- oder Programmordner übernehmen. None = keine (neue) Datei."""
    from .konfig import programmordner

    for ordner in dict.fromkeys([speicher.pfad(""), programmordner()]):
        pfad = ordner / IMPORT_DATEI
        if not pfad.is_file():
            continue
        text = pfad.read_text(encoding="utf-8-sig")
        kennung = hashlib.sha1(text.encode()).hexdigest()[:16]
        if kennung in speicher.einstellungen().get("zustand_importe", []):
            return None
        befunde, fehler = lesen(text, {z.id for z in stand.zimmer})
        erg = anwenden(stand, befunde)
        erg.fehler = fehler
        speicher.einstellung_setzen("zustand_importe", speicher.einstellungen().get("zustand_importe", []) + [kennung])
        return erg
    return None
