"""Vorgänge für „Heute“: Was jetzt zu tun ist, in einer ruhigen, priorisierten Liste.

Jeder Vorgang hat genau eine Hauptaktion (``ziel``), die direkt dorthin führt, wo er bearbeitet wird. Ähnliches wird
gebündelt („27 Buchungen eintragen“ statt 27 Zeilen). Drei Stufen:

* ``dringend`` – zuerst klären: Konflikte, Einzug ohne Reinigung, Anreisen in ≤ 3 Tagen ohne Zimmer, Eintragen für
  Anreisen in ≤ 2 Tagen
* ``bald``     – als Nächstes: Anreisen ohne Zimmer (14 Tage), Eintragen, Erinnerungen, Posteingang, kritische
  Engpass-Wochen, neuer Gebäudeplan
* ``info``     – zur Info: Abreisen heute/morgen, Reinigungen heute, Facility-Checks, knappe Wochen

Rein, ohne Qt – die Daten kommen aus denselben Funktionen wie die Kacheln der Startseite.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from . import cockpit, eintragen
from . import zimmerplan as zp

STUFEN = ("dringend", "bald", "info")
STUFE_TEXT = {"dringend": "Zuerst klären", "bald": "Als Nächstes", "info": "Zur Info"}
ANREISE_TAGE = 14


@dataclass
class Vorgang:
    id: str                  # stabil, z. B. „anreise:2026-10-26“
    stufe: str               # dringend | bald | info
    titel: str
    detail: str
    aktion: str              # Beschriftung der Hauptaktion
    ziel: str                # konflikte | anreise:<iso> | eintragen | posteingang | termin:<id> | reinigung | engpaesse
    #                          | abreisen | gebaeudeplan | facility | umzug:<id>
    datum: date | None = None
    erledigen: str = ""      # Termin-ID: direkt „erledigt“ setzbar

    @property
    def rang(self) -> int:
        """Innerhalb einer Stufe: erst Konflikte, dann Zimmer vergeben, eintragen/Posteingang, Engpässe, Erinnerungen."""
        art = self.id.split(":")[0].split("_")[0]
        return {"konflikte": 0, "umzug": 0, "reinigung": 0, "anreise": 1, "eintragen": 2, "mail": 2,
                "gebaeudeplan": 2, "engpass": 3, "termin": 4}.get(art, 5)

    @property
    def sortierung(self) -> tuple:
        return STUFEN.index(self.stufe), self.rang, self.datum or date.max, self.titel


WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _tag(d: date, heute: date) -> str:
    n = (d - heute).days
    return {0: "heute", 1: "morgen", -1: "gestern"}.get(n, f"{WOCHENTAGE[d.weekday()]} {d:%d.%m.}")


def _personen(n: int) -> str:
    return f"{n} Person" if n == 1 else f"{n} Personen"


def zimmerplan_vorgaenge(stand: zp.Planstand, heute: date, engpaesse: bool = True) -> list[Vorgang]:
    erg: list[Vorgang] = []
    # Konflikte: geplantes Zimmer inzwischen belegt/gesperrt
    kon = zp.konflikte(stand.lage, heute)
    if kon:
        erg.append(Vorgang("konflikte", "dringend", f"{len(kon)} Planung{'en' if len(kon) > 1 else ''} mit Konflikt",
                           "; ".join(k.text for k in kon[:2]) + (" …" if len(kon) > 2 else ""), "Lösen …", "konflikte",
                           min(k.von for k in kon)))
    for u in stand.lage.umzuege.values():
        if u.status == "konflikt":
            erg.append(Vorgang(f"umzug:{u.id}", "dringend", f"Umzug {u.name}", f"{u.text} – {u.hinweis}",
                               "Umzug öffnen", f"umzug:{u.id}", u.ab))
    # Anreisen ohne Zimmer
    for kennung, tag, titel, bedarf in stand.anreisen(heute):
        if tag > heute + timedelta(days=ANREISE_TAGE):
            continue
        ohne = sum(1 for b in bedarf if not stand.zugewiesen(b.schluessel))
        if not ohne:
            continue
        stufe = "dringend" if tag <= heute + timedelta(days=3) else "bald"
        erg.append(Vorgang(f"anreise:{tag.isoformat()}", stufe, f"Anreise {_tag(tag, heute)}: {_personen(ohne)} ohne Zimmer",
                           f"{titel} · {len(bedarf) - ohne} von {len(bedarf)} haben ein Zimmer", "Zuteilen",
                           f"anreise:{tag.isoformat()}", tag))
    # Im Belegungssystem eintragen
    offen = [z for z in eintragen.offen(stand.lage, heute, heute + timedelta(days=14)) if not z.haken]
    if offen:
        erste = min(z.von for z in offen)
        n_erste = sum(1 for z in offen if z.von == erste)
        stufe = "dringend" if erste <= heute + timedelta(days=2) else "bald"
        erg.append(Vorgang("eintragen", stufe, f"{len(offen)} Buchung{'en' if len(offen) > 1 else ''} im Belegungssystem "
                           "eintragen", f"als Erstes: {_tag(erste, heute)} ({n_erste})", "Eintragen", "eintragen", erste))
    # Reinigung
    dringend, heute_offen = cockpit.reinigung_heute(stand, heute)
    if dringend:
        erg.append(Vorgang("reinigung_dringend", "dringend", f"{len(dringend)} Zimmer vor dem Einzug noch nicht gereinigt",
                           ", ".join(r.zimmer.kurz for r in dringend[:5]), "Reinigungsliste", "reinigung", heute))
    if heute_offen:
        erg.append(Vorgang("reinigung", "info", f"{len(heute_offen)} Reinigung{'en' if len(heute_offen) > 1 else ''} heute",
                           ", ".join(r.zimmer.kurz for r in heute_offen[:6]), "Reinigungsliste", "reinigung", heute))
    # Abreisen heute/morgen
    ab = cockpit.abreisen(stand, heute)
    if ab:
        erg.append(Vorgang("abreisen", "info", f"{_personen(len(ab))} reis{'t' if len(ab) == 1 else 'en'} heute/morgen ab",
                           ", ".join(f"{a.name.split(',')[0]} ({a.zimmer.removeprefix('GS-')})" for a in ab[:4])
                           + (" …" if len(ab) > 4 else ""), "Abreiseliste", "abreisen", heute))
    # Facility-Checks
    checks = [c for c in eintragen.facility_checks(stand.lage, heute - timedelta(days=7), heute + timedelta(days=14))
              if not c.haken]
    if checks:
        erg.append(Vorgang("facility", "info", f"{len(checks)} Facility-Check{'s' if len(checks) > 1 else ''} nach Auszug",
                           ", ".join(c.zimmer.removeprefix("GS-") for c in checks[:5]), "Ansehen", "facility",
                           min(c.bis for c in checks)))
    # Engpässe nach Planung (5 Wochen)
    if engpaesse:
        try:
            wochen = [w for _j, w in eintragen.nach_planung(stand, heute, 5).wochen]
        except Exception:                      # noqa: BLE001 – Engpass-Rechnung darf die Liste nicht verhindern
            wochen = []
        kritisch = [w for w in wochen if any(w.stufe(a) == "kritisch" for a in ("gesamt", "emr", "doppel"))]
        knapp = [w for w in wochen if w not in kritisch and any(w.stufe(a) == "knapp" for a in ("gesamt", "emr", "doppel"))]
        for liste, stufe, wort in ((kritisch, "bald", "kritisch"), (knapp, "info", "knapp")):
            if liste:
                w = liste[0]
                erg.append(Vorgang(f"engpass_{wort}", stufe, f"Zimmer {wort}: {w.text.split(' · ')[0]}"
                                   + (f" und {len(liste) - 1} weitere Woche{'n' if len(liste) > 2 else ''}" if len(liste) > 1 else ""),
                                   f"nach Planung {w.gesamt} frei · EMR {w.emr} · Doppel {w.doppel}", "Engpässe", "engpaesse"))
    return erg


def termin_vorgaenge(termine: list, heute: date) -> list[Vorgang]:
    erg = []
    for t in termine:
        if not t.faellig(heute):
            continue
        alt = (heute - t.datum).days
        erg.append(Vorgang(f"termin:{t.id}", "bald", t.titel, f"{_tag(t.datum, heute)}" + (f" · {t.text}" if t.text else "")
                           + (f" · seit {alt} Tagen fällig" if alt > 2 else ""), "Öffnen",
                           f"person:{t.person}" if t.person else "termine", t.datum, erledigen=t.id))
    return erg


def posteingang_vorgaenge(eingaenge: list, arten: dict) -> list[Vorgang]:
    erg = []
    for x in eingaenge:
        if x.status not in ("offen", "zu prüfen"):
            continue
        rest = x.offen_zu_pruefen
        detail = ("noch abzuhaken: " + ", ".join(rest)) if rest else "noch nicht bearbeitet"
        erg.append(Vorgang(f"mail:{x.id}", "bald", f"{arten.get(x.art, x.art)}: {x.name or x.betreff or '–'}", detail,
                           "Öffnen", "posteingang"))
    return erg


def sammeln(stand: zp.Planstand | None, heute: date, termine: list | None = None, eingaenge: list | None = None,
            arten: dict | None = None, neuer_plan: bool = False, engpaesse: bool = True) -> list[Vorgang]:
    """Alle Vorgänge, sortiert: Stufe, Datum, Titel."""
    erg: list[Vorgang] = []
    if stand is not None:
        erg += zimmerplan_vorgaenge(stand, heute, engpaesse)
    erg += termin_vorgaenge(termine or [], heute)
    erg += posteingang_vorgaenge(eingaenge or [], arten or {})
    if neuer_plan:
        erg.append(Vorgang("gebaeudeplan", "bald", "Neuer Gebäudeplan im Ordner",
                           "Im Ordner „Gebaeudeplan“ liegt eine neue Word-Datei", "Importieren", "gebaeudeplan"))
    return sorted(erg, key=lambda v: v.sortierung)
