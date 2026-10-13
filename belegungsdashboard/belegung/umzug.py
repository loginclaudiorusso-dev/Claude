"""Umzug während des Aufenthalts: Wer schon eingezogen ist (Gebäudeplan oder angereist), wechselt ab einem Tag
in ein anderes Zimmer.

Der Gebäudeplan wird nicht verändert. Ein Umzug ist eine eigene Planung obenauf:

* Im alten Zimmer endet der Aufenthalt am Umzugstag. Dort ist dann Auszugsreinigung, danach ist das Zimmer frei.
* Im neuen Zimmer steht die Person ab dem Umzugstag bis zur Abreise als „geplant“. Damit erscheint der Umzug unter
  Aufgaben → Eintragen, bis er im Belegungssystem umgebucht ist.
* Zeigt der nächste Gebäudeplan die Person im neuen Zimmer, ist der Umzug **erledigt** und wird nicht mehr
  angewendet.
* Ist die Person nicht mehr im alten Zimmer (z. B. früher abgereist), ist er **hinfällig**.

Rein, ohne Qt. Gespeichert in ``importe/umzuege.json``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from . import protokoll, speicher
from . import zimmerplan as zp
from .gebaeudeplan import Belegung

DATEI = f"{speicher.IMPORT_ORDNER}/umzuege.json"
TOLERANZ = timedelta(days=3)          # Gebäudeplan darf beim Umzugstag ein paar Tage abweichen
STATUS_TEXT = {"aktiv": "aktiv", "erledigt": "im Belegungssystem umgebucht",
               "hinfaellig": "hinfällig – Person nicht mehr im alten Zimmer", "konflikt": "Konflikt"}


@dataclass
class Umzug:
    id: str
    schluessel: str             # Bewohner-Schlüssel (Anreise-/UWT-Person oder „gp:…“)
    name: str
    massnahme: str
    von_zimmer: str
    nach_zimmer: str
    ab: date                    # Umzugstag: Auszug alt, Einzug neu
    grund: str = ""
    erstellt: str = ""
    status: str = ""            # beim Anwenden gesetzt: aktiv | erledigt | hinfaellig | konflikt
    hinweis: str = ""           # Konflikt-Grund
    belegt: bool = False        # True: Umzug ist erfolgt/steht fest – neues Zimmer gilt als belegt (nicht nur geplant)

    @property
    def text(self) -> str:
        return (f"{self.name}: {self.von_zimmer.removeprefix('GS-')} → {self.nach_zimmer.removeprefix('GS-')} "
                f"ab {self.ab:%d.%m.%Y}")

    @property
    def status_text(self) -> str:
        t = STATUS_TEXT.get(self.status, self.status)
        if self.status == "aktiv":
            t = "belegt (im Zimmerplan bestätigt)" if self.belegt else "geplant – im Belegungssystem umbuchen"
        return f"{t}: {self.hinweis}" if self.hinweis else t

    def zu_dict(self) -> dict:
        return {"id": self.id, "schluessel": self.schluessel, "name": self.name, "massnahme": self.massnahme,
                "von_zimmer": self.von_zimmer, "nach_zimmer": self.nach_zimmer, "ab": self.ab.isoformat(),
                "grund": self.grund, "erstellt": self.erstellt, "belegt": self.belegt}

    @staticmethod
    def aus_dict(d: dict) -> "Umzug":
        return Umzug(d["id"], d.get("schluessel", ""), d.get("name", ""), d.get("massnahme", ""), d["von_zimmer"],
                     d["nach_zimmer"], date.fromisoformat(d["ab"]), d.get("grund", ""), d.get("erstellt", ""),
                     belegt=bool(d.get("belegt")))


def laden() -> list[Umzug]:
    erg = []
    for d in speicher.lesen(DATEI, {}).get("umzuege", []):
        try:
            erg.append(Umzug.aus_dict(d))
        except (KeyError, ValueError, TypeError):
            continue
    return erg


def _schreiben(umzuege: list[Umzug]) -> None:
    speicher.schreiben(DATEI, {"umzuege": [u.zu_dict() for u in umzuege]})


# ---------------------------------------------------------------------------------------
# Anwenden auf die Lage
# ---------------------------------------------------------------------------------------

def _gleiche_person(b: Belegung, schluessel: str, name: str) -> bool:
    if b.person and b.person == schluessel:
        return True
    return bool(b.name) and zp._namenswoerter(b.name) == zp._namenswoerter(name)


def quelle_finden(lage: zp.Lage, u: Umzug) -> Belegung | None:
    """Die Belegung im alten Zimmer, die den Umzugstag enthält."""
    for b in lage.belegungen.get(u.von_zimmer, []):
        if b.art in ("belegt", "geplant") and b.name != zp.PIVOT_NAME and b.von <= u.ab <= b.bis \
                and _gleiche_person(b, u.schluessel, u.name):
            return b
    return None


def _erledigt(lage: zp.Lage, u: Umzug) -> bool:
    """Steht die Person laut Gebäudeplan schon im neuen Zimmer (um den Umzugstag herum)?"""
    woerter = zp._namenswoerter(u.name)
    return any(b.art == "belegt" and not b.person and b.name and woerter and woerter <= zp._namenswoerter(b.name)
               and b.von <= u.ab + TOLERANZ and b.bis >= u.ab
               for b in lage.belegungen.get(u.nach_zimmer, []))


def anwenden(lage: zp.Lage, umzuege: list[Umzug]) -> None:
    """Umzüge (nach Datum) auf die Lage anwenden; setzt ``status`` und füllt ``lage.umzuege``."""
    for u in sorted(umzuege, key=lambda u: (u.ab, u.erstellt)):
        lage.umzuege[u.id] = u
        if u.nach_zimmer not in lage.zimmer or u.von_zimmer not in lage.zimmer:
            u.status, u.hinweis = "hinfaellig", "Zimmer gibt es nicht mehr"
            continue
        if _erledigt(lage, u):
            u.status = "erledigt"
            continue
        alt = quelle_finden(lage, u)
        if alt is None:
            u.status = "hinfaellig"
            continue
        liste = [x for x in lage.belegungen[u.von_zimmer] if x is not alt]
        if u.ab > alt.von:
            liste.append(replace(alt, bis=u.ab, umzug=u.id))
        lage.belegungen[u.von_zimmer] = liste
        schluessel = alt.person or u.schluessel
        geschlecht = alt.grund if alt.art == "geplant" else zp.geschlecht_raten(alt.name)
        neu = Belegung(u.nach_zimmer, max(u.ab, alt.von), alt.bis, "belegt" if u.belegt else "geplant", alt.name,
                       alt.massnahme, geschlecht, schluessel, u.id)
        ohne = frozenset({schluessel})
        u.status, u.hinweis = "aktiv", ""
        andere = lage._relevant(u.nach_zimmer, neu.von, neu.bis, ohne)
        if any(x.art == "gesperrt" for x in andere):
            u.status, u.hinweis = "konflikt", "neues Zimmer ist inzwischen gesperrt"
        elif lage.freie_betten(u.nach_zimmer, neu.von, neu.bis, ohne) <= 0:
            namen = ", ".join(x.name for x in andere if x.art in ("belegt", "geplant"))[:80]
            u.status, u.hinweis = "konflikt", f"neues Zimmer ist inzwischen belegt ({namen})"
        lage.belegungen.setdefault(u.nach_zimmer, []).append(neu)


def zur_person(lage: zp.Lage, schluessel: str) -> list[Umzug]:
    return sorted((u for u in lage.umzuege.values() if u.schluessel == schluessel), key=lambda u: u.ab)


# ---------------------------------------------------------------------------------------
# Planen
# ---------------------------------------------------------------------------------------

def belegung_zu(stand: zp.Planstand, zid: str, schluessel: str, name: str, heute: date | None = None) -> Belegung | None:
    """Aktuelle bzw. nächste Belegung der Person in diesem Zimmer."""
    heute = heute or date.today()
    kandidaten = [b for b in stand.lage.belegungen.get(zid, []) if b.art in ("belegt", "geplant")
                  and b.name != zp.PIVOT_NAME and _gleiche_person(b, schluessel, name)]
    if not kandidaten:
        return None
    return min(kandidaten, key=lambda b: (b.bis < heute, abs((b.von - heute).days) if b.von > heute else 0))


def bedarf_zu(stand: zp.Planstand, b: Belegung, ab: date) -> zp.Bedarf:
    """Bedarf für den Teil ab dem Umzugstag (für die Regeln) – aus der Liste, sonst aus dem Gebäudeplan."""
    liste = next((x for x in stand.bedarf if x.schluessel == b.person), None) if b.person else None
    if liste is None:
        bw = zp.bewohner_aus(stand, b)
        liste = bw.bedarf
    if liste is not None:
        return replace(liste, von=max(ab, b.von), bis=b.bis)
    gruppe = zp.belegung_gruppe(b) or "Reha"
    z = stand.lage.zimmer.get(b.zimmer)
    # Tier steht nicht im Gebäudeplan: laut ZKL, sonst wer im UG von Haus 3.1 wohnt (nur mit Tier), hat eins
    from . import zkl

    tier = zkl.hat_tier(stand.lage, b)
    return zp.Bedarf(zp.gp_schluessel(b.name), b.name, b.massnahme, gruppe, max(ab, b.von), b.bis,
                     zp.geschlecht_raten(b.name), True, tier=tier if tier is not None else bool(z and zp.nur_tier(z)))


def schluessel_zu(stand: zp.Planstand, b: Belegung) -> str:
    return b.person or zp.bewohner_aus(stand, b).schluessel


def pruefen(stand: zp.Planstand, b: Belegung, nach: str, ab: date) -> tuple[str | None, str | None]:
    """(Fehler, Hinweis): Fehler = geht nicht; Hinweis = geht, verletzt aber eine Regel (Ausnahme von Hand)."""
    lage = stand.lage
    z = lage.zimmer.get(nach)
    if z is None or not z.aktiv:
        return "Dieses Zimmer gehört nicht zum Internat.", None
    if nach == b.zimmer:
        return "Das ist das bisherige Zimmer.", None
    if ab < b.von or ab > b.bis:
        return f"Der Umzugstag muss im Aufenthalt liegen ({b.von:%d.%m.} – {b.bis:%d.%m.%Y}).", None
    bd = bedarf_zu(stand, b, ab)
    ohne = frozenset({schluessel_zu(stand, b), bd.schluessel})
    if zp.nur_doppel(z, bd.gruppe):
        return f"{z.kurz} ist ein Doppelzimmer – {zp.DOPPEL_GRUND}.", None
    if lage.freie_betten(nach, bd.von, bd.bis, ohne) <= 0:
        return f"{z.kurz} ist vom {bd.von:%d.%m.} bis {bd.bis:%d.%m.%Y} belegt oder gesperrt.", None
    grund = zp.passt(lage, z, bd, ohne)
    if lage.mitbewohner(nach, bd.von, bd.bis, ohne) and grund:
        namen = ", ".join(m.name for m in lage.mitbewohner(nach, bd.von, bd.bis, ohne))
        return f"In {z.kurz} wohnt im Zeitraum schon {namen} – dorthin geht es nicht ({grund}).", None
    if grund and "nur Männer" in grund and bd.geschlecht_geschaetzt:
        grund += " (Geschlecht nur geschätzt)"
    return None, grund


def auswahl(stand: zp.Planstand, b: Belegung, ab: date) -> tuple[list[zp.Zimmer], list[tuple[zp.Zimmer, str]]]:
    """Mögliche Zielzimmer ab dem Umzugstag: (zulässig, Ausnahmen mit Grund) – nach Haus und Nummer."""
    gut, ausnahmen = [], []
    for z in sorted(stand.lage.zimmer.values(), key=lambda z: (zp._haus_sort(z.haus), z.nummer)):
        if not z.aktiv or z.id == b.zimmer:
            continue
        fehler, hinweis = pruefen(stand, b, z.id, ab)
        if fehler:
            continue
        if hinweis:
            ausnahmen.append((z, hinweis))
        else:
            gut.append(z)
    return gut, ausnahmen


def speichern(stand: zp.Planstand, b: Belegung, nach: str, ab: date, grund: str = "", alt_id: str | None = None,
              quelle: str = "Umzug", belegt: bool = False) -> Umzug:
    """Umzug anlegen bzw. ``alt_id`` ersetzen und protokollieren. ``stand`` ohne den alten Umzug laden!"""
    umzuege = [u for u in laden() if u.id != alt_id]
    u = Umzug(alt_id or uuid.uuid4().hex[:12], schluessel_zu(stand, b), b.name, b.massnahme, b.zimmer, nach, ab,
              grund.strip(), datetime.now().isoformat(timespec="seconds"), belegt=belegt)
    _schreiben(umzuege + [u])
    protokoll.eintragen([{"aktion": "Umzug" if not alt_id else "Umzug geändert", "name": u.name, "person": u.schluessel,
                          "alt": u.von_zimmer, "neu": u.nach_zimmer, "von": ab.isoformat(), "quelle": quelle}])
    return u


def status_setzen(uid: str, belegt: bool, quelle: str = "Umzug") -> Umzug | None:
    """Umzug als belegt (erfolgt) markieren bzw. zurück auf geplant."""
    umzuege = laden()
    u = next((x for x in umzuege if x.id == uid), None)
    if u is None:
        return None
    u.belegt = belegt
    _schreiben(umzuege)
    protokoll.eintragen([{"aktion": "Umzug als belegt markiert" if belegt else "Umzug zurück auf geplant", "name": u.name,
                          "person": u.schluessel, "alt": u.von_zimmer, "neu": u.nach_zimmer, "von": u.ab.isoformat(),
                          "quelle": quelle}])
    return u


def entfernen(uid: str, quelle: str = "Umzug") -> Umzug | None:
    umzuege = laden()
    weg = next((u for u in umzuege if u.id == uid), None)
    if weg is None:
        return None
    _schreiben([u for u in umzuege if u.id != uid])
    protokoll.eintragen([{"aktion": "Umzug zurückgenommen", "name": weg.name, "person": weg.schluessel,
                          "alt": weg.nach_zimmer, "neu": weg.von_zimmer, "von": weg.ab.isoformat(), "quelle": quelle}])
    return weg


def aufraeumen(lage: zp.Lage, heute: date | None = None, tage: int = 60) -> int:
    """Erledigte und hinfällige Umzüge, die länger als ``tage`` zurückliegen, aus der Datei entfernen."""
    heute = heute or date.today()
    weg = {u.id for u in lage.umzuege.values() if u.status in ("erledigt", "hinfaellig") and u.ab < heute - timedelta(days=tage)}
    if weg:
        _schreiben([u for u in laden() if u.id not in weg])
    return len(weg)


def standard_tag(b: Belegung, heute: date | None = None) -> date:
    """Vorschlag für den Umzugstag: heute (bzw. Anreise, wenn sie noch kommt), höchstens der Abreisetag."""
    heute = heute or date.today()
    return min(max(heute, b.von), b.bis)
