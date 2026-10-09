"""Einheitsliste: ein Format für alle Anreise- und UWT-Listen (z. B. von Claude aus beliebigen Listen umgebaut).

Eine Zeile je Person, Kopfzeile (Reihenfolge egal, Groß-/Kleinschreibung egal):

    Art | Nachname | Vorname | TN-ID | Gruppe | Maßnahme | Klasse | Anreise | Abreise | Internat |
    Geschlecht | Tier | DZ-Partner | Zimmer | Bemerkung | Quelle

* Art: „Anreise“ oder „UWT“
* Gruppe: EMR, ASS, RVL, RVT, Reha, UWT, Gast, Mieter
* Anreise/Abreise: TT.MM.JJJJ (EMR: Anreise = Datum laut Liste, den Vortag rechnet das Programm)
* Internat/Tier: ja/nein · Geschlecht: m/w/d/leer · DZ-Partner (UWT): gleiche Nummer = gemeinsames
  Doppelzimmer, „-“ = allein

Anreise-Zeilen werden je Anreisetag und EMR/übrige wie eine Anreiseliste übernommen, UWT-Zeilen je
Klasse und Zeitraum als Block mit Namen. Rein, ohne Qt.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from . import anreiseliste, speicher, uwt
from .importe import datum_lesen, tabelle_lesen

SPALTEN = ["Art", "Nachname", "Vorname", "TN-ID", "Gruppe", "Maßnahme", "Klasse", "Anreise", "Abreise", "Internat",
           "Geschlecht", "Tier", "DZ-Partner", "Zimmer", "Bemerkung", "Quelle"]
GRUPPEN = {"EMR", "ASS", "RVL", "RVT", "REHA", "UWT", "GAST", "MIETER"}
_MASSNAHME_STANDARD = {"ASS": "GS ASS", "RVL": "GS RVL", "RVT": "GS RVT", "EMR": "EMR ASS", "GAST": "Gast",
                       "MIETER": "Miete Goslar", "REHA": "", "UWT": ""}


def _norm(v) -> str:
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower().replace("ß", "ss").replace("ä", "a").replace("ö", "o")
                  .replace("ü", "u"))


def _ja(v) -> bool:
    return _norm(v) in ("ja", "j", "x", "yes", "1", "true", "wahr")


@dataclass
class Ergebnis:
    anreisen: list[anreiseliste.Anreiseliste] = field(default_factory=list)
    uwt: uwt.UwtListe | None = None
    klassen: dict[str, list[uwt.KlassenPerson]] = field(default_factory=dict)
    hinweise: list[str] = field(default_factory=list)
    ohne_abreise: list[str] = field(default_factory=list)


def _kopf(zeilen: list[list]) -> tuple[int, dict[str, int]] | None:
    for i, z in enumerate(zeilen[:10]):
        spalten = {_norm(v): j for j, v in enumerate(z) if v not in (None, "")}
        if {"art", "nachname", "anreise", "abreise"} <= set(spalten):
            return i, spalten
    return None


def ist_einheitsliste(pfad: Path) -> bool:
    if Path(pfad).suffix.lower() not in (".xlsx", ".xlsm", ".csv", ".txt"):
        return False
    try:
        return _kopf(tabelle_lesen(Path(pfad)).zeilen) is not None
    except Exception:
        return False


def lesen(pfad: Path) -> Ergebnis:
    pfad = Path(pfad)
    zeilen = tabelle_lesen(pfad).zeilen
    k = _kopf(zeilen)
    if k is None:
        raise ValueError("Keine Kopfzeile der Einheitsliste (Art, Nachname, Anreise, Abreise …) gefunden.")
    start, sp = k
    erg = Ergebnis()

    def zelle(z: list, name: str):
        i = sp.get(_norm(name))
        return z[i] if i is not None and i < len(z) else None

    tage: dict[tuple[date, str], list[anreiseliste.Person]] = {}
    bloecke: dict[tuple[str, date, date], list[tuple]] = {}
    for nr, z in enumerate(zeilen[start + 1:], start=start + 2):
        nachname = str(zelle(z, "Nachname") or "").strip()
        if not nachname:
            continue
        vorname = str(zelle(z, "Vorname") or "").strip()
        name = f"{nachname}, {vorname}" if vorname else nachname
        art = _norm(zelle(z, "Art"))
        gruppe = str(zelle(z, "Gruppe") or "").strip().upper()
        if art == "uwt" or gruppe == "UWT":
            art, gruppe = "uwt", "UWT"
        anreise, abreise = datum_lesen(zelle(z, "Anreise")), datum_lesen(zelle(z, "Abreise"))
        if anreise is None:
            erg.hinweise.append(f"Zeile {nr} ({name}): keine gültige Anreise – übersprungen.")
            continue
        if abreise is not None and abreise < anreise:
            erg.hinweise.append(f"Zeile {nr} ({name}): Abreise vor Anreise – Abreise ignoriert.")
            abreise = None
        if gruppe and gruppe not in GRUPPEN:
            erg.hinweise.append(f"Zeile {nr} ({name}): Gruppe „{gruppe}“ unbekannt – aus der Maßnahme bestimmt.")
            gruppe = ""
        tn = re.sub(r"\.0$", "", str(zelle(z, "TN-ID") or "").strip())
        geschlecht = _norm(zelle(z, "Geschlecht"))[:1]
        geschlecht = geschlecht if geschlecht in ("m", "w", "d") else ""
        bemerkung = str(zelle(z, "Bemerkung") or "").strip()
        if art == "uwt":
            klasse = re.sub(r"\s+", "", str(zelle(z, "Klasse") or "").upper())
            if not klasse:
                m = re.search(r"\b([A-Z]{2,5}\s?\d{2})\b", str(zelle(z, "Maßnahme") or "").upper())
                klasse = m.group(1).replace(" ", "") if m else ""
            if not klasse:
                erg.hinweise.append(f"Zeile {nr} ({name}): UWT ohne Klasse – übersprungen.")
                continue
            if abreise is None:
                erg.ohne_abreise.append(f"{name} (UWT {klasse}, Anreise {anreise:%d.%m.%Y})")
                continue                     # UWT-Block braucht ein Ende
            dz = str(zelle(z, "DZ-Partner") or "").strip()
            bloecke.setdefault((klasse, anreise, abreise), []).append(
                (tn or "n-" + _norm(name), name, str(zelle(z, "Zimmer") or "").strip(), geschlecht, dz, bemerkung))
            continue
        massnahme = str(zelle(z, "Maßnahme") or "").strip() or _MASSNAHME_STANDARD.get(gruppe, "")
        if gruppe and gruppe not in ("REHA", "EMR") and anreiseliste_gruppe(massnahme) != gruppe:
            massnahme = f"{massnahme} {_MASSNAHME_STANDARD[gruppe]}".strip()   # Gruppe muss aus der Maßnahme folgen
        emr = gruppe == "EMR" or "EMR" in massnahme.upper()
        if emr and "EMR" not in massnahme.upper():
            massnahme = f"EMR {massnahme}".strip()                          # EMR muss aus der Maßnahme folgen
        internat_roh = zelle(z, "Internat")
        if internat_roh in (None, ""):
            erg.hinweise.append(f"Zeile {nr} ({name}): Internat leer – als „ja“ gewertet.")
        internat = True if internat_roh in (None, "") else _ja(internat_roh)
        if abreise is None and internat:
            erg.ohne_abreise.append(f"{name} ({massnahme or gruppe or 'Anreise'}, Anreise {anreise:%d.%m.%Y})")
        p = anreiseliste.Person(name=name, massnahme=massnahme, anreise=anreise, internat=internat,
                                gruppe="EMR" if emr else "Reha", tn_id=tn, abreise=abreise, geschlecht=geschlecht,
                                tier=_ja(zelle(z, "Tier")), bemerkung=bemerkung)
        if abreise is not None:
            p.abreise_quelle = "hand"        # ausdrücklich angegeben – nicht durch die EMR-Regel ersetzen
        tage.setdefault((anreise, "EMR" if emr else "Reha"), []).append(p)

    for (tag, gruppe), personen in sorted(tage.items()):
        liste = anreiseliste.Anreiseliste(f"{pfad.name} ({tag:%d.%m.%Y})", tag, gruppe, personen)
        for p in personen:
            p.liste = liste.schluessel
        erg.anreisen.append(liste)

    if bloecke:
        bl, personen = [], []
        klassen: dict[str, dict[str, uwt.KlassenPerson]] = {}
        for (klasse, von, bis), leute in sorted(bloecke.items(), key=lambda x: (x[0][1], x[0][0])):
            bl.append(uwt.Block(klasse, len(leute), von, bis))
            mit_liste = any(dz for *_x, dz, _b in leute)
            nummern = [m.group(1) for *_x, dz, _b in leute if (m := re.match(r"^(\d+)", dz))]
            for tn, name, zimmer, g, dz, bem in leute:
                personen.append(uwt.UwtPerson(tn, name, klasse, zimmer))
                m = re.match(r"^(\d+)", dz)
                if mit_liste:
                    d = f"{klasse}:{m.group(1)}" if m and nummern.count(m.group(1)) >= 2 else "allein"
                    klassen.setdefault(klasse, {})[tn] = uwt.KlassenPerson(tn, name, g, d, bem)
        erg.uwt = uwt.UwtListe(pfad.name, bl, personen)
        erg.klassen = {k: list(v.values()) for k, v in klassen.items()}
    if erg.ohne_abreise:
        erg.hinweise.insert(0, f"{len(erg.ohne_abreise)} Personen ohne Abreise: " + "; ".join(erg.ohne_abreise[:8])
                            + (" …" if len(erg.ohne_abreise) > 8 else "") + " – bitte nachtragen.")
    return erg


def anreiseliste_gruppe(massnahme: str) -> str:
    from .zimmerplan import gruppe_von

    return gruppe_von(massnahme, "REHA").upper()


def importieren(erg: Ergebnis) -> dict[str, int]:
    """Übernimmt Anreisen (wie Anreiselisten), UWT-Blöcke und DZ-Partner. Gibt Zähler zurück."""
    z = {"neu": 0, "aktualisiert": 0, "entfernt": 0, "uwt_bloecke": 0, "uwt_personen": 0}
    for liste in erg.anreisen:
        b = anreiseliste.importieren(liste)
        z["neu"] += b.neu
        z["aktualisiert"] += b.aktualisiert
        z["entfernt"] += len(b.entfernt)
    if erg.uwt is not None:
        neu, ersetzt = uwt.importieren(erg.uwt)
        z["uwt_bloecke"] = neu + ersetzt
        z["uwt_personen"] = len(erg.uwt.personen)
    if erg.klassen:
        uwt.klassen_importieren(erg.klassen, erg.uwt.datei if erg.uwt else "", [])
    return z


# ---------------------------------------------------------------------------------------
# Ordner „Listen“: Einheitslisten dort ablegen – werden beim Start übernommen
# ---------------------------------------------------------------------------------------

EINGANG = "Listen"
_KENNUNGEN = f"{speicher.IMPORT_ORDNER}/listen_eingang.json"


def eingangsordner() -> Path:
    return speicher.pfad(EINGANG)


def automatisch_importieren(ordner: Path | None = None) -> list[str]:
    ordner = ordner or eingangsordner()
    if not ordner.is_dir():
        return []
    dateien = sorted((p for p in ordner.iterdir() if p.suffix.lower() in (".xlsx", ".xlsm", ".csv")
                      and not p.name.startswith("~$")), key=lambda p: p.stat().st_mtime)
    bekannt = speicher.lesen(_KENNUNGEN, {})
    meldungen = []
    for p in dateien:
        kennung = int(p.stat().st_mtime)
        if bekannt.get(p.name) == kennung or not ist_einheitsliste(p):
            continue
        try:
            erg = lesen(p)
            z = importieren(erg)
        except Exception:
            continue
        bekannt[p.name] = kennung
        if not erg.anreisen and erg.uwt is None:
            continue                         # leere Vorlage
        text = f"{p.name}: {z['neu']} Anreisen neu, {z['aktualisiert']} aktualisiert"
        if z["uwt_bloecke"]:
            text += f", {z['uwt_bloecke']} UWT-Blöcke ({z['uwt_personen']} Personen)"
        if erg.ohne_abreise:
            text += f" – {len(erg.ohne_abreise)} ohne Abreise"
        meldungen.append(text)
    if meldungen:
        speicher.schreiben(_KENNUNGEN, bekannt)
    return meldungen
