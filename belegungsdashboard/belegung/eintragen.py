"""Aufgaben im Zimmerplan: was im Belegungssystem noch einzutragen ist, und wo es eng wird.

* Eintragen: Alles, was hier geplant ist, aber (noch) nicht im Gebäudeplan steht. Nach dem Eintragen
  im Belegungssystem abhaken; steht die Person im nächsten Gebäudeplan, verschwindet die Zeile von
  selbst. Ändert sich das geplante Zimmer, ist der Haken wieder weg (neu eintragen!).
* Engpässe: je Woche die wenigsten freien Zimmer (gesamt, EMR-Etagen, Doppelzimmer für die UWT).

Rein, ohne Qt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from . import speicher
from . import zimmerplan as zp

DATEI = f"{speicher.IMPORT_ORDNER}/eingetragen.json"


@dataclass
class Zeile:
    person: str
    name: str
    massnahme: str
    zimmer: str
    von: date
    bis: date
    haken: bool = False

    @property
    def schluessel(self) -> str:
        return f"{self.person}|{self.zimmer}|{self.von.isoformat()}"


def _haken() -> dict[str, str]:
    return speicher.lesen(DATEI, {}).get("haken", {})


def offen(lage: zp.Lage, heute: date | None = None, bis: date | None = None) -> list[Zeile]:
    """Geplante (noch nicht im Gebäudeplan stehende) Zimmer ab heute, optional nur Anreisen bis ``bis``."""
    heute = heute or date.today()
    haken = _haken()
    zeilen = []
    for zid, bs in lage.belegungen.items():
        for b in bs:
            if b.art != "geplant" or b.bis < heute or (bis and b.von > bis):
                continue
            z = Zeile(b.person, b.name, b.massnahme, zid, b.von, b.bis)
            z.haken = z.schluessel in haken
            zeilen.append(z)
    return sorted(zeilen, key=lambda z: (z.von, z.massnahme, z.zimmer, z.name))


def setzen(zeilen: list[Zeile], an: bool) -> None:
    roh = speicher.lesen(DATEI, {})
    haken = roh.get("haken", {})
    jetzt = datetime.now().isoformat(timespec="seconds")
    for z in zeilen:
        if an:
            haken[z.schluessel] = jetzt
        else:
            haken.pop(z.schluessel, None)
    # alte Haken (Anreise lange vorbei) aufräumen
    grenze = (date.today() - timedelta(days=60)).isoformat()
    haken = {k: v for k, v in haken.items() if k.rsplit("|", 1)[-1] >= grenze}
    speicher.schreiben(DATEI, {"haken": haken})


def kopiertext(zeilen: list[Zeile]) -> str:
    """Tabulator-getrennt (Zimmer, Name, Maßnahme, von, bis) – zum Einfügen in Excel oder als Spickzettel."""
    return "\n".join(f"{z.zimmer.removeprefix('GS-')}\t{z.name}\t{z.massnahme}\t{z.von:%d.%m.%Y}\t{z.bis:%d.%m.%Y}"
                     for z in zeilen)


# ---------------------------------------------------------------------------------------
# Engpässe
# ---------------------------------------------------------------------------------------

GRENZEN = {"gesamt": (10, 5), "emr": (4, 2), "doppel": (3, 1)}   # (knapp unter, kritisch unter)


@dataclass
class Woche:
    montag: date
    gesamt: int          # freie Zimmer (ohne Gästezimmer), wenigster Tag der Woche
    emr: int             # frei in Haus 2, Etage 1–2
    doppel: int          # ganz freie Doppelzimmer in Haus 3.2/3.3/6 (UWT)

    def stufe(self, art: str) -> str:
        knapp, kritisch = GRENZEN[art]
        wert = getattr(self, art)
        return "kritisch" if wert < kritisch else ("knapp" if wert < knapp else "ok")

    @property
    def gesamtstufe(self) -> str:
        stufen = {self.stufe(a) for a in GRENZEN}
        return "kritisch" if "kritisch" in stufen else ("knapp" if "knapp" in stufen else "ok")


def engpaesse(lage: zp.Lage, heute: date | None = None, wochen: int = 12) -> list[Woche]:
    """Freie Zimmer je Woche nach heutigem Stand (Gebäudeplan + Planungen; künftige Anreisen ohne Liste
    fehlen noch – die Zahlen sind also eher zu hoch)."""
    heute = heute or date.today()
    montag = heute - timedelta(days=heute.weekday())
    zimmer = [z for z in lage.zimmer.values() if z.aktiv and not z.gaeste]
    emr = [z for z in zimmer if zp.erlaubt(z, "EMR")]
    doppel = [z for z in zimmer if z.betten > 1 and zp.erlaubt(z, "UWT")]
    ergebnis = []
    for w in range(wochen):
        start = montag + timedelta(weeks=w)
        tage = [start + timedelta(days=i) for i in range(7) if start + timedelta(days=i) >= heute]
        frei = {z.id: all(lage.status_am(z.id, t)[0] == "frei" for t in tage) for z in zimmer}
        ergebnis.append(Woche(start, sum(frei.values()), sum(frei[z.id] for z in emr), sum(frei[z.id] for z in doppel)))
    return ergebnis


# ---------------------------------------------------------------------------------------
# Facility-Check: nach einem langen Aufenthalt Elektrik prüfen und Fensterwartung machen
# ---------------------------------------------------------------------------------------

FACILITY_DATEI = f"{speicher.IMPORT_ORDNER}/facility.json"
FACILITY_MONATE = 6                 # ab so vielen Monaten Aufenthalt (einstellbar)
FACILITY_AUFGABE = "Elektrik prüfen, Fensterwartung"


def facility_tage() -> int:
    monate = int(speicher.einstellungen().get("facility_monate", FACILITY_MONATE) or FACILITY_MONATE)
    return round(monate * 30.44)


@dataclass
class FacilityCheck:
    zimmer: str
    name: str
    massnahme: str
    von: date
    bis: date                       # Auszug
    haken: bool = False

    @property
    def schluessel(self) -> str:
        return f"{self.zimmer}|{self.bis.isoformat()}"

    @property
    def monate(self) -> int:
        return max(round(((self.bis - self.von).days + 1) / 30.44), 1)

    @property
    def text(self) -> str:
        return (f"Zimmer {self.zimmer.removeprefix('GS-')}: Auszug {self.bis:%d.%m.} nach {self.monate} Monaten – "
                f"{FACILITY_AUFGABE}")


def lange_belegung(b: zp.Belegung, personen: list[zp.Belegung], tage: int) -> bool:
    """Echter Auszug nach mindestens ``tage`` Tagen (keine Pivot-Ergänzung, keine nahtlose Fortsetzung)."""
    if b.art not in ("belegt", "geplant") or b.name == zp.PIVOT_NAME or (b.bis - b.von).days + 1 < tage:
        return False
    return not any(x is not b and x.name == zp.PIVOT_NAME and x.von == b.bis + timedelta(days=1) for x in personen)


def _facility_roh() -> dict:
    roh = speicher.lesen(FACILITY_DATEI, {})
    roh.setdefault("haken", {})
    roh.setdefault("gemeldet", {})
    return roh


def facility_checks(lage: zp.Lage, von: date, bis: date, tage: int | None = None) -> list[FacilityCheck]:
    """Auszüge nach langem Aufenthalt zwischen von und bis (nach Datum und Zimmer)."""
    tage = tage or facility_tage()
    haken = _facility_roh()["haken"]
    erg = []
    for zid, bs in lage.belegungen.items():
        z = lage.zimmer.get(zid)
        if z is None or not z.aktiv:
            continue
        personen = [b for b in bs if b.art in ("belegt", "geplant")]
        for b in personen:
            if von <= b.bis <= bis and lange_belegung(b, personen, tage):
                c = FacilityCheck(zid, b.name, b.massnahme, b.von, b.bis)
                c.haken = c.schluessel in haken
                erg.append(c)
    # ein Eintrag je Zimmer und Auszugstag (Doppelzimmer: beide ziehen aus)
    eindeutig = {c.schluessel: c for c in sorted(erg, key=lambda c: c.von)}
    return sorted(eindeutig.values(), key=lambda c: (c.bis, zp._haus_sort(zid_haus(c.zimmer)), c.zimmer))


def zid_haus(zid: str) -> str:
    teile = zid.split("-")
    return teile[1] if len(teile) > 2 else ""


def facility_setzen(c: FacilityCheck, an: bool) -> None:
    roh = _facility_roh()
    if an:
        roh["haken"][c.schluessel] = datetime.now().isoformat(timespec="minutes")
    else:
        roh["haken"].pop(c.schluessel, None)
    grenze = (date.today() - timedelta(days=180)).isoformat()
    roh["haken"] = {k: v for k, v in roh["haken"].items() if k.rsplit("|", 1)[-1] >= grenze}
    speicher.schreiben(FACILITY_DATEI, roh)


def facility_zu_melden(lage: zp.Lage, heute: date, tage_vorher: int = 3) -> list[FacilityCheck]:
    """Offene Facility-Checks mit Auszug in den nächsten Tagen, die noch nicht gemeldet wurden (einmal je Zimmer)."""
    gemeldet = _facility_roh()["gemeldet"]
    return [c for c in facility_checks(lage, heute, heute + timedelta(days=tage_vorher))
            if not c.haken and c.schluessel not in gemeldet]


def facility_gemeldet(checks: list[FacilityCheck]) -> None:
    roh = _facility_roh()
    jetzt = date.today().isoformat()
    for c in checks:
        roh["gemeldet"][c.schluessel] = jetzt
    grenze = (date.today() - timedelta(days=180)).isoformat()
    roh["gemeldet"] = {k: v for k, v in roh["gemeldet"].items() if v >= grenze}
    speicher.schreiben(FACILITY_DATEI, roh)
