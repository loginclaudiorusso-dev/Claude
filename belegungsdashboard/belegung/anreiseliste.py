"""Anreiselisten des Internats Goslar.

Aufbau (siehe Beispiele „Anreiseliste 21-10-2026“ und „Anreiseliste 12-10-2026 EMR“):
* Zeile 1 ist der Titel mit dem Anreisedatum, optional mit Gruppe („EMR“).
* Darunter die Kopfzeile; welche Spalten es gibt, schwankt von Liste zu Liste.
* Gebraucht werden nur Name, Maßnahme, Internat (ja/nein) und – wenn vorhanden – TN-ID und Abreise.

Personen werden über die TN-ID wiedererkannt. Ein erneuter Upload derselben Liste aktualisiert
Name/Maßnahme/Internat, behält aber die von Hand eingetragene Abreise und Erinnerung. Wer in
der neuen Fassung einer Liste fehlt, wird entfernt (die Liste ist der aktuelle Stand).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from . import speicher
from .importe import _norm, datum_lesen, tabelle_lesen

STANDORT = "BFW GS"
DATEI = f"{speicher.IMPORT_ORDNER}/anreisen_goslar.json"
MANUELL = "manuell"

_DATUM_TITEL = re.compile(r"(\d{1,2})[-._](\d{1,2})[-._](\d{4}|\d{2})\b")
_DATUM_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


@dataclass
class Person:
    name: str
    massnahme: str
    anreise: date
    internat: bool | None
    gruppe: str = "Reha"
    tn_id: str = ""
    abreise: date | None = None
    liste: str = MANUELL                # Schlüssel der Liste, aus der die Person stammt
    erinnerung_tage: int | None = None  # None = keine Erinnerung
    erinnerung_kanal: str = ""          # outlook | mail | ics | app
    erinnerung_id: str = ""             # Outlook-EntryID, um den Termin später zu ändern/löschen
    erledigt: bool = False              # Erinnerung quittiert

    @property
    def schluessel(self) -> str:
        return f"id:{self.tn_id}" if self.tn_id else f"name:{self.name.lower()}|{self.anreise.isoformat()}"

    @property
    def erinnerung_am(self) -> date | None:
        if self.abreise is None or self.erinnerung_tage is None:
            return None
        return self.abreise - timedelta(days=self.erinnerung_tage)

    def zu_dict(self) -> dict:
        return {"name": self.name, "massnahme": self.massnahme, "anreise": self.anreise.isoformat(),
                "internat": self.internat, "gruppe": self.gruppe, "tn_id": self.tn_id,
                "abreise": self.abreise.isoformat() if self.abreise else None, "liste": self.liste,
                "erinnerung_tage": self.erinnerung_tage, "erinnerung_kanal": self.erinnerung_kanal,
                "erinnerung_id": self.erinnerung_id, "erledigt": self.erledigt}

    @staticmethod
    def aus_dict(d: dict) -> "Person":
        return Person(
            name=d.get("name", ""), massnahme=d.get("massnahme", ""), anreise=date.fromisoformat(d["anreise"]),
            internat=d.get("internat"), gruppe=d.get("gruppe") or "Reha", tn_id=str(d.get("tn_id") or ""),
            abreise=date.fromisoformat(d["abreise"]) if d.get("abreise") else None, liste=d.get("liste") or MANUELL,
            erinnerung_tage=d.get("erinnerung_tage"), erinnerung_kanal=d.get("erinnerung_kanal") or "",
            erinnerung_id=d.get("erinnerung_id") or "", erledigt=bool(d.get("erledigt", False)),
        )


@dataclass
class Anreiseliste:
    datei: str
    datum: date
    gruppe: str
    personen: list[Person]
    hinweise: list[str] = field(default_factory=list)

    @property
    def schluessel(self) -> str:
        return f"{self.datum.isoformat()}|{self.gruppe}"

    @property
    def mit_internat(self) -> int:
        return sum(1 for p in self.personen if p.internat)


# ---------------------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------------------

def _datum_aus_text(text: str) -> date | None:
    m = _DATUM_TITEL.search(text)
    if m:
        t, mo, j = (int(x) for x in m.groups())
        j += 2000 if j < 100 else 0
        try:
            return date(j, mo, t)
        except ValueError:
            pass
    m = _DATUM_ISO.search(text)
    if m:
        try:
            return date(*(int(x) for x in m.groups()))
        except ValueError:
            pass
    return None


def _spalte(kopf: list, *pruefungen) -> int | None:
    """Erste Spalte, deren normierter Kopf eine der Prüfungen erfüllt (Reihenfolge = Vorrang)."""
    norm = [_norm(v) for v in kopf]
    for pruefe in pruefungen:
        for i, n in enumerate(norm):
            if n and pruefe(n):
                return i
    return None


def _internat(wert) -> bool | None:
    n = _norm(wert)
    if n.startswith("ja") or n in ("x", "j", "1"):
        return True
    if n.startswith("nein") or n in ("n", "0"):
        return False
    return None


def _tn_id(wert) -> str:
    if wert is None:
        return ""
    if isinstance(wert, float) and wert.is_integer():
        wert = int(wert)
    return str(wert).strip()


def liste_lesen(pfad: Path) -> Anreiseliste:
    tab = tabelle_lesen(Path(pfad))
    zeilen = tab.zeilen
    kopf_idx = None
    for i, z in enumerate(zeilen[:15]):
        norm = [_norm(v) for v in z]
        if any(n.startswith("name") for n in norm) and any(n == "internat" for n in norm):
            kopf_idx = i
            break
    if kopf_idx is None:
        raise ValueError("Keine Kopfzeile mit den Spalten „Name“ und „Internat“ gefunden – ist das eine Anreiseliste?")
    kopf = zeilen[kopf_idx]

    titel = " ".join(str(v) for z in zeilen[:kopf_idx] for v in z if v not in (None, ""))
    datum = _datum_aus_text(titel) or _datum_aus_text(Path(pfad).stem)
    if datum is None:
        raise ValueError("Das Anreisedatum steht weder im Titel („Anreiseliste TT-MM-JJJJ“) noch im Dateinamen.")

    sp_name = _spalte(kopf, lambda n: n.startswith("namevorname"), lambda n: n.startswith("name"))
    sp_internat = _spalte(kopf, lambda n: n == "internat")
    sp_massn = _spalte(kopf, lambda n: n.startswith("massn"), lambda n: n == "massnahme")
    sp_id = _spalte(kopf, lambda n: n in ("tnid", "tnnr", "teilnehmerid", "teilnehmernr", "id"))
    sp_kt = _spalte(kopf, lambda n: n in ("kt", "kostentraeger", "kostentrager"))
    sp_abreise = _spalte(kopf, lambda n: n.startswith("abreise"), lambda n: n in ("ende", "bis", "massnahmeende"))

    def zelle(z: list, i: int | None):
        return z[i] if i is not None and i < len(z) else None

    emr_titel = "emr" in titel.lower() or "emr" in Path(pfad).stem.lower()
    personen, hinweise = [], []
    for nr, z in enumerate(zeilen[kopf_idx + 1:], start=kopf_idx + 2):
        name = str(zelle(z, sp_name) or "").strip()
        if not name:
            if any(v not in (None, "") for v in z):
                hinweise.append(f"Zeile {nr}: kein Name – übersprungen.")
            continue
        massnahme = str(zelle(z, sp_massn) or "").strip()
        kt = str(zelle(z, sp_kt) or "")
        gruppe = "EMR" if (emr_titel or "emr" in massnahme.lower() or "emr" in kt.lower()) else "Reha"
        internat = _internat(zelle(z, sp_internat))
        if internat is None:
            hinweise.append(f"Zeile {nr} ({name}): Internat „{zelle(z, sp_internat) or ''}“ nicht eindeutig – "
                            "als „nein“ gewertet.")
        abreise = datum_lesen(zelle(z, sp_abreise))
        if abreise is not None and abreise < datum:
            abreise = None
        personen.append(Person(name=name, massnahme=massnahme, anreise=datum, internat=bool(internat),
                               gruppe=gruppe, tn_id=_tn_id(zelle(z, sp_id)), abreise=abreise))
    if not personen:
        raise ValueError("In der Liste stehen keine Personen.")
    gruppe = "EMR" if emr_titel else ("EMR" if all(p.gruppe == "EMR" for p in personen) else "Reha")
    liste = Anreiseliste(Path(pfad).name, datum, gruppe, personen, hinweise)
    for p in personen:
        p.liste = liste.schluessel
    return liste


# ---------------------------------------------------------------------------------------
# Bestand
# ---------------------------------------------------------------------------------------

@dataclass
class Bericht:
    neu: int = 0
    aktualisiert: int = 0
    entfernt: list[Person] = field(default_factory=list)   # mit evtl. Outlook-Terminen, die weg müssen


def uebernehmen(bestand: list[Person], liste: Anreiseliste) -> tuple[list[Person], Bericht]:
    """Liste in den Bestand einarbeiten (rein, ohne Dateizugriff)."""
    bericht = Bericht()
    alt = {p.schluessel: p for p in bestand}
    neue_schluessel = set()
    for p in liste.personen:
        k = p.schluessel
        neue_schluessel.add(k)
        vorher = alt.get(k)
        if vorher is None:
            alt[k] = p
            bericht.neu += 1
            continue
        vorher.name, vorher.massnahme, vorher.internat, vorher.gruppe = p.name, p.massnahme, p.internat, p.gruppe
        if vorher.anreise != p.anreise:   # Anreise verschoben
            vorher.anreise = p.anreise
            if vorher.abreise and vorher.abreise < p.anreise:
                vorher.abreise = None
        vorher.liste = p.liste
        if p.abreise and not vorher.abreise:
            vorher.abreise = p.abreise
        bericht.aktualisiert += 1
    for k, p in list(alt.items()):
        if p.liste == liste.schluessel and k not in neue_schluessel:
            bericht.entfernt.append(alt.pop(k))
    return sorted(alt.values(), key=lambda p: (p.anreise, p.name.lower())), bericht


def laden() -> tuple[list[Person], dict]:
    roh = speicher.lesen(DATEI, {})
    personen = []
    for d in roh.get("personen", []):
        try:
            personen.append(Person.aus_dict(d))
        except (KeyError, ValueError):
            continue
    return personen, roh.get("listen", {})


def speichern(personen: list[Person], listen: dict) -> None:
    speicher.schreiben(DATEI, {"personen": [p.zu_dict() for p in personen], "listen": listen})


def importieren(liste: Anreiseliste) -> Bericht:
    personen, listen = laden()
    personen, bericht = uebernehmen(personen, liste)
    listen[liste.schluessel] = {"datei": liste.datei, "datum": liste.datum.isoformat(), "gruppe": liste.gruppe,
                                "personen": len(liste.personen), "internat": liste.mit_internat,
                                "importiert_am": datetime.now().isoformat(timespec="seconds")}
    speichern(personen, listen)
    return bericht


def person_speichern(person: Person, alter_schluessel: str | None = None) -> None:
    personen, listen = laden()
    personen = [p for p in personen if p.schluessel not in (alter_schluessel, person.schluessel)]
    personen.append(person)
    speichern(sorted(personen, key=lambda p: (p.anreise, p.name.lower())), listen)


def person_loeschen(schluessel: str) -> None:
    personen, listen = laden()
    speichern([p for p in personen if p.schluessel != schluessel], listen)


def alle_loeschen() -> list[Person]:
    personen, _ = laden()
    speicher.pfad(DATEI).unlink(missing_ok=True)
    return personen


# ---------------------------------------------------------------------------------------
# Auswertung
# ---------------------------------------------------------------------------------------

def eintraege(personen: list[Person], standard_wochen: int = 0) -> list[dict]:
    """Nur Personen mit Internat zählen zur Belegung. Ohne Abreise: Standarddauer oder nur Termin."""
    ergebnis = []
    for p in personen:
        if not p.internat:
            continue
        bis, nur_termin = p.abreise, False
        if bis is None:
            if standard_wochen > 0:
                bis = p.anreise + timedelta(weeks=standard_wochen) - timedelta(days=1)
            else:
                bis, nur_termin = p.anreise, True
        ergebnis.append({"kategorie": "Anreise", "standort": STANDORT, "von": p.anreise.isoformat(),
                         "bis": bis.isoformat(), "anzahl": 1, "bezeichnung": f"{p.name} ({p.massnahme or p.gruppe})",
                         "gruppe": p.massnahme or p.gruppe, "nur_termin": nur_termin})
    return ergebnis


def faellige_erinnerungen(personen: list[Person], heute: date) -> list[Person]:
    """Erinnerungen, deren Termin erreicht ist und die noch nicht quittiert wurden."""
    return sorted((p for p in personen if p.erinnerung_am is not None and not p.erledigt
                   and p.erinnerung_am <= heute <= p.abreise + timedelta(days=2)),
                  key=lambda p: p.abreise)


def abreisen(personen: list[Person], von: date, bis: date) -> list[Person]:
    return sorted((p for p in personen if p.abreise and von <= p.abreise <= bis), key=lambda p: p.abreise)
