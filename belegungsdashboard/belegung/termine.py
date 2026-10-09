"""Terminkalender im Dashboard – funktioniert ohne Outlook.

Termine entstehen automatisch aus den Daten oder werden von Hand angelegt:

* ``notiz``   – Notiz zur Anreise („Duschstuhl“, „kommt mit Partner“ …) am Ankunftstag,
                Erinnerung ``notiz_tage`` Tage vorher (Standard 3). Ändert sich die Notiz,
                erinnert das Dashboard erneut.
* ``abreise`` – Abreise-Erinnerung einer Person (Daten → Anreisen, „Erinnern“).
* ``anreise`` / ``uwt`` – Anreisen und UWT-Blöcke als Kalendereintrag, ohne Erinnerung.
* ``eigen``   – eigene Termine mit Erinnerung X Tage vorher.

Fällige Erinnerungen meldet das Dashboard beim Start, alle 15 Minuten im Infobereich
(Windows-Benachrichtigung) und auf der Seite „Termine“ – jeden Tag erneut, bis sie
als erledigt abgehakt sind.
"""

from __future__ import annotations

import uuid
import zlib
from dataclasses import dataclass
from datetime import date, timedelta

from . import anreiseliste, speicher

DATEI = "termine.json"
ARTEN = {"notiz": "Notiz zur Anreise", "abreise": "Abreise", "anreise": "Anreise", "uwt": "UWT", "eigen": "Eigener Termin"}
NOTIZ_TAGE = 3          # Standard-Vorlauf für Notizen zur Anreise
ABREISE_TAGE_EMR = 1    # Abreisen: Erinnerung je Tag gesammelt, EMR einen Tag vorher …
ABREISE_TAGE = 2        # … alle anderen (inkl. UWT-Blöcke) zwei Tage vorher; -1 = keine Erinnerung
WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
RUECKBLICK = 7          # so lange bleiben unerledigte Erinnerungen nach dem Termin sichtbar


@dataclass
class Termin:
    id: str
    datum: date
    titel: str
    text: str = ""
    art: str = "eigen"
    erinnern_am: date | None = None
    erledigt: bool = False
    person: str = ""            # Schlüssel der Anreise-Person (notiz/abreise)
    vorlauf: int = 0            # Tage vor dem Termin (nur eigene)

    def faellig(self, heute: date) -> bool:
        return (self.erinnern_am is not None and not self.erledigt and self.erinnern_am <= heute
                and self.datum >= heute - timedelta(days=RUECKBLICK))


# ---------------------------------------------------------------------------------------
# Ablage
# ---------------------------------------------------------------------------------------

def _roh() -> dict:
    roh = speicher.lesen(DATEI, {})
    roh.setdefault("eigene", [])
    roh.setdefault("erledigt", [])
    roh.setdefault("gemeldet", {})
    return roh


def einstellungen() -> dict:
    e = speicher.einstellungen().get("termine", {})
    return {"notiz_tage": int(e.get("notiz_tage", NOTIZ_TAGE)), "hintergrund": bool(e.get("hintergrund", True)),
            "autostart": bool(e.get("autostart", False)),
            "abreise_tage_emr": int(e.get("abreise_tage_emr", ABREISE_TAGE_EMR)),
            "abreise_tage": int(e.get("abreise_tage", ABREISE_TAGE))}


def einstellung_setzen(**werte) -> None:
    e = speicher.einstellungen().get("termine", {})
    e.update(werte)
    speicher.einstellung_setzen("termine", e)


def eigene() -> list[Termin]:
    erledigt = set(_roh()["erledigt"])
    ergebnis = []
    for d in _roh()["eigene"]:
        datum = date.fromisoformat(d["datum"])
        vorlauf = int(d.get("vorlauf", 1))
        ergebnis.append(Termin(d["id"], datum, d.get("titel", ""), d.get("text", ""), "eigen",
                               datum - timedelta(days=vorlauf) if vorlauf >= 0 else None, d["id"] in erledigt,
                               vorlauf=vorlauf))
    return ergebnis


def eigenen_speichern(t: Termin) -> Termin:
    roh = _roh()
    if not t.id:
        t.id = f"eigen:{uuid.uuid4().hex[:10]}"
    roh["eigene"] = [d for d in roh["eigene"] if d["id"] != t.id] + [
        {"id": t.id, "datum": t.datum.isoformat(), "titel": t.titel, "text": t.text, "vorlauf": t.vorlauf}]
    roh["gemeldet"].pop(t.id, None)
    speicher.schreiben(DATEI, roh)
    return t


def eigenen_loeschen(tid: str) -> None:
    roh = _roh()
    roh["eigene"] = [d for d in roh["eigene"] if d["id"] != tid]
    roh["erledigt"] = [i for i in roh["erledigt"] if i != tid]
    speicher.schreiben(DATEI, roh)


def erledigt_setzen(t: Termin, erledigt: bool = True) -> None:
    """Persönliche Abreise-Erinnerungen werden an der Person quittiert, alles andere hier."""
    if t.art == "abreise" and t.person and t.id == f"abreise:{t.person}":
        personen, _ = anreiseliste.laden()
        for p in personen:
            if p.schluessel == t.person:
                p.erledigt = erledigt
                anreiseliste.person_speichern(p)
        return
    roh = _roh()
    ids = [i for i in roh["erledigt"] if i != t.id]
    if erledigt:
        ids.append(t.id)
    roh["erledigt"] = ids
    speicher.schreiben(DATEI, roh)


def zu_melden(termine: list[Termin], heute: date) -> list[Termin]:
    """Fällige Erinnerungen, die heute noch nicht gemeldet wurden."""
    gemeldet = _roh()["gemeldet"]
    return [t for t in termine if t.faellig(heute) and gemeldet.get(t.id) != heute.isoformat()]


def gemeldet_setzen(termine: list[Termin], heute: date) -> None:
    roh = _roh()
    for t in termine:
        roh["gemeldet"][t.id] = heute.isoformat()
    grenze = (heute - timedelta(days=60)).isoformat()
    roh["gemeldet"] = {k: v for k, v in roh["gemeldet"].items() if v >= grenze}
    speicher.schreiben(DATEI, roh)


# ---------------------------------------------------------------------------------------
# Termine aus den Daten
# ---------------------------------------------------------------------------------------

def _kennung(text: str) -> str:
    return f"{zlib.crc32(text.encode('utf-8')):08x}"


def _vorher(tag: date, tage: int) -> date | None:
    return tag - timedelta(days=tage) if tage >= 0 else None


def aus_personen(personen: list[anreiseliste.Person], notiz_tage: int = NOTIZ_TAGE,
                 erledigt: set[str] | None = None,
                 abreise_tage: tuple[int, int] = (ABREISE_TAGE_EMR, ABREISE_TAGE)) -> list[Termin]:
    """``abreise_tage``: Vorlauf (EMR, andere) für die gesammelte Abreise-Erinnerung je Tag."""
    erledigt = erledigt or set()
    ergebnis: list[Termin] = []
    tage: dict[date, list[anreiseliste.Person]] = {}
    abreisetage: dict[tuple[date, str], list[anreiseliste.Person]] = {}
    for p in personen:
        ankunft = anreiseliste.ankunft(p)
        tage.setdefault(ankunft, []).append(p)
        wer = f"{p.name} ({p.massnahme or p.gruppe})"
        if p.bemerkung.strip():
            tid = f"notiz:{p.schluessel}:{_kennung(p.bemerkung.strip())}"
            vor = f" (EMR, Liste {p.anreise:%d.%m.})" if ankunft != p.anreise else ""
            ergebnis.append(Termin(tid, ankunft, f"{p.name}: {p.bemerkung.strip()}",
                                   f"Anreise {wer} am {ankunft:%d.%m.%Y}{vor}.\nNotiz: {p.bemerkung.strip()}",
                                   "notiz", ankunft - timedelta(days=max(notiz_tage, 0)), tid in erledigt, p.schluessel))
        if p.abreise is not None and p.erinnerung_am is None:
            if p.internat:                                       # ohne eigene Erinnerung: je Tag gesammelt
                kat = "emr" if anreiseliste.ist_emr(p) else "andere"
                abreisetage.setdefault((p.abreise, kat), []).append(p)
        elif p.abreise is not None:
            ergebnis.append(Termin(f"abreise:{p.schluessel}", p.abreise, f"Abreise {p.name}",
                                   f"{wer} reist am {p.abreise:%d.%m.%Y} ab.", "abreise", p.erinnerung_am,
                                   p.erledigt, p.schluessel))
    def sammel(tid: str, tag: date, titel: str, ps: list, art: str, erinnern: date | None) -> Termin:
        namen = ", ".join(p.name for p in ps[:6]) + (f" und {len(ps) - 6} weitere" if len(ps) > 6 else "")
        gruppen = sorted({p.massnahme or p.gruppe for p in ps})
        return Termin(tid, tag, f"{titel}: {len(ps)} {'Person' if len(ps) == 1 else 'Personen'} ({', '.join(gruppen)[:60]})",
                      namen, art, erinnern, tid in erledigt, ps[0].schluessel if len(ps) == 1 else "")

    for tag, ps in sorted(tage.items()):
        ergebnis.append(sammel(f"anreise:{tag.isoformat()}", tag, "Anreise", ps, "anreise", None))
    for (tag, kat), ps in sorted(abreisetage.items()):
        vorlauf = abreise_tage[0] if kat == "emr" else abreise_tage[1]
        ergebnis.append(sammel(f"abreisetag:{tag.isoformat()}:{kat}", tag, "Abreise", ps, "abreise", _vorher(tag, vorlauf)))
    return ergebnis


def aus_uwt(bloecke: list[dict], abreise_tage: int = -1, erledigt: set[str] | None = None) -> list[Termin]:
    erledigt = erledigt or set()
    ergebnis = []
    for b in bloecke:
        von, bis = date.fromisoformat(b["anreise"]), date.fromisoformat(b["abreise"])
        n = int(b.get("anzahl", 0))
        ergebnis.append(Termin(f"uwt:{b['klasse']}:{b['anreise']}:an", von, f"UWT {b['klasse']} reist an ({n})",
                               f"Block bis {bis:%d.%m.%Y}", "uwt"))
        tid = f"uwt:{b['klasse']}:{b['anreise']}:ab"
        ergebnis.append(Termin(tid, bis, f"UWT {b['klasse']} reist ab ({n})", f"Block ab {von:%d.%m.%Y}", "uwt",
                               _vorher(bis, abreise_tage), tid in erledigt))
    return ergebnis


def alle(personen: list[anreiseliste.Person] | None = None, bloecke: list[dict] | None = None,
         notiz_tage: int | None = None) -> list[Termin]:
    if personen is None:
        personen, _ = anreiseliste.laden()
    if bloecke is None:
        from . import uwt

        bloecke = uwt.laden()
    e = einstellungen()
    if notiz_tage is None:
        notiz_tage = e["notiz_tage"]
    erledigt = set(_roh()["erledigt"])
    termine = (aus_personen(personen, notiz_tage, erledigt, (e["abreise_tage_emr"], e["abreise_tage"]))
               + aus_uwt(bloecke, e["abreise_tage"], erledigt) + eigene())
    return sorted(termine, key=lambda t: (t.datum, list(ARTEN).index(t.art), t.titel))


def meldetext(termine: list[Termin]) -> tuple[str, str]:
    """Titel und Text für eine Windows-Benachrichtigung."""
    if len(termine) == 1:
        t = termine[0]
        text = t.titel + (f"\n{t.text.splitlines()[0]}" if t.text and t.art in ("abreise", "anreise") else "")
        return f"Erinnerung · {WOCHENTAGE[t.datum.weekday()]} {t.datum:%d.%m.}", text
    zeilen = [f"{t.datum:%d.%m.} {t.titel}" for t in termine[:4]]
    if len(termine) > 4:
        zeilen.append(f"… und {len(termine) - 4} weitere")
    return f"{len(termine)} Erinnerungen fällig", "\n".join(zeilen)
