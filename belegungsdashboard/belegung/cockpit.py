"""Startseite („Mein Dashboard“): Kacheln, die sich jede Nutzerin selbst zusammenstellt.

Hier stehen der Katalog der Kacheln und die Daten dahinter – rein, ohne Qt. Die Anordnung (Reihenfolge,
Breite) liegt in den Einstellungen unter ``dashboard``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from . import speicher
from . import zimmerplan as zp


@dataclass(frozen=True)
class KachelArt:
    id: str
    titel: str
    beschreibung: str
    breite: int = 1          # 1 = halbe Breite, 2 = ganze Breite


KATALOG: list[KachelArt] = [
    KachelArt("heute", "Zimmer heute", "Frei, belegt, gesperrt und Anreisen ohne Zimmer"),
    KachelArt("erinnerungen", "Jetzt erinnern", "Fällige Erinnerungen und Wiedervorlagen zum Abhaken"),
    KachelArt("posteingang", "Posteingang", "Offene Mails und Abbrüche mit offener Prüfliste"),
    KachelArt("anreisen", "Anreisen", "Die nächsten 7 Tage – wie viele schon ein Zimmer haben", 2),
    KachelArt("abreisen", "Abreisen", "Heute und morgen – wer aus welchem Zimmer auszieht"),
    KachelArt("reinigung", "Reinigung", "Was heute gereinigt werden muss, offene Konflikte zuerst"),
    KachelArt("eintragen", "Im Belegungssystem eintragen", "Geplant, aber noch nicht eingetragen (14 Tage)"),
    KachelArt("engpaesse", "Engpässe", "Freie Zimmer je Woche – gesamt, EMR-Etagen, Doppelzimmer"),
    KachelArt("facility", "Facility-Check", "Auszüge nach langem Aufenthalt: Elektrik, Fenster"),
    KachelArt("notizen", "Neueste Notizen", "Notizen zu Personen und Zimmern mit Wiedervorlage", 2),
    KachelArt("belegung", "Belegung je Standort", "Belegte Plätze heute (aus der Pivot-Datei)", 2),
    KachelArt("schnell", "Schnellzugriff", "Suche, Person anlegen, Gebäudeplan, Termin"),
    KachelArt("optimierung", "Belegung optimieren", "Regelverstöße, bessere Zimmer und Tausche prüfen"),
]
ARTEN = {k.id: k for k in KATALOG}
STANDARD = ["heute", "erinnerungen", "anreisen", "abreisen", "reinigung", "eintragen", "engpaesse"]


# ---------------------------------------------------------------------------------------
# Anordnung
# ---------------------------------------------------------------------------------------

def anordnung() -> list[dict]:
    """[{"id", "breite"}] – unbekannte/doppelte Kacheln fallen weg; leer → Standard."""
    roh = speicher.einstellungen().get("dashboard")
    ergebnis, gesehen = [], set()
    for k in roh if isinstance(roh, list) else []:
        if isinstance(k, dict) and k.get("id") in ARTEN and k["id"] not in gesehen:
            gesehen.add(k["id"])
            ergebnis.append({"id": k["id"], "breite": 2 if k.get("breite") == 2 else 1})
    if not ergebnis and not isinstance(roh, list):
        ergebnis = [{"id": i, "breite": ARTEN[i].breite} for i in STANDARD]
    return ergebnis


TITEL_STANDARD = ("Start", "Mein Dashboard – selbst zusammengestellt")


def titel() -> tuple[str, str]:
    """(Titel, Untertitel) der Startseite – im Anpassen-Modus änderbar."""
    roh = speicher.einstellungen().get("start_titel") or {}
    t = str(roh.get("titel") or "").strip() or TITEL_STANDARD[0]
    u = roh.get("untertitel")
    return t, (TITEL_STANDARD[1] if u is None else str(u).strip())


def titel_speichern(t: str, u: str) -> None:
    speicher.einstellung_setzen("start_titel", {"titel": t.strip()[:40], "untertitel": u.strip()[:80]})


def anordnung_speichern(kacheln: list[dict]) -> None:
    speicher.einstellung_setzen("dashboard", [{"id": k["id"], "breite": k.get("breite", 1)} for k in kacheln])


def verschieben(kacheln: list[dict], kid: str, vor: str | None) -> list[dict]:
    """Kachel ``kid`` vor die Kachel ``vor`` setzen (None = ans Ende)."""
    k = next((x for x in kacheln if x["id"] == kid), None)
    if k is None or kid == vor:
        return kacheln
    rest = [x for x in kacheln if x["id"] != kid]
    i = next((n for n, x in enumerate(rest) if x["id"] == vor), len(rest))
    return rest[:i] + [k] + rest[i:]


# ---------------------------------------------------------------------------------------
# Daten der Kacheln
# ---------------------------------------------------------------------------------------

def zimmer_heute(stand: zp.Planstand, heute: date) -> dict[str, int]:
    z = {"frei": 0, "belegt": 0, "gesperrt": 0}
    for zi in stand.zimmer:
        if not zi.aktiv or zi.gaeste:
            continue
        status, _ = stand.lage.status_am(zi.id, heute)
        if status == "teilweise":
            z["frei"] += 1
            z["belegt"] += 1
        elif status in ("geplant", "belegt"):
            z["belegt"] += 1
        else:
            z[status] = z.get(status, 0) + 1
    z["ohne_zimmer"] = sum(1 for b in stand.bedarf
                           if heute <= b.von <= heute + timedelta(weeks=8) and not stand.zugewiesen(b.schluessel))
    return z


@dataclass
class AnreiseTag:
    tag: date
    text: str
    personen: int
    mit_zimmer: int


def anreisen(stand: zp.Planstand, heute: date, tage: int = 7) -> list[AnreiseTag]:
    ergebnis = []
    for _k, tag, text, bs in stand.anreisen(heute):
        if tag > heute + timedelta(days=tage):
            break
        ergebnis.append(AnreiseTag(tag, text, len(bs), sum(1 for b in bs if stand.zugewiesen(b.schluessel))))
    return ergebnis


@dataclass
class Abreise:
    tag: date
    name: str
    massnahme: str
    zimmer: str


def abreisen(stand: zp.Planstand, heute: date, tage: int = 1) -> list[Abreise]:
    ergebnis = []
    for zid, bs in stand.lage.belegungen.items():
        for b in bs:
            if b.art in ("belegt", "geplant") and b.name and b.name != zp.PIVOT_NAME \
                    and heute <= b.bis <= heute + timedelta(days=tage):
                ergebnis.append(Abreise(b.bis, b.name, b.massnahme, zid))
    return sorted(ergebnis, key=lambda a: (a.tag, zp._haus_sort(a.zimmer.split("-")[1]), a.zimmer))


def reinigung_heute(stand: zp.Planstand, heute: date) -> tuple[list[zp.Reinigung], list[zp.Reinigung]]:
    """(offene Konflikte – jemand zieht heute/morgen ein –, alle noch offenen Reinigungen von heute)."""
    from . import reinigungsliste as rl

    zpv = stand.zimmer_pivot
    rs = zp.reinigungen(stand.lage, heute - timedelta(days=14), heute + timedelta(days=1),
                        zpv.zeitraum[1] if zpv else None, zpv.zeitraum[0] if zpv else None,
                        bool(speicher.einstellungen().get("reinigung_anreisetag", False)))
    fertig = rl.erledigt()
    kon = rl.konflikte(rs, heute, fertig)
    offen_heute = [r for r in rs if r.tag == heute and rl.prioritaet(r, heute, fertig) < 9 and r not in kon]
    return kon, offen_heute
