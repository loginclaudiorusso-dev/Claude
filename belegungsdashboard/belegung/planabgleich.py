"""Neuen Gebäudeplan vor dem Übernehmen prüfen: Was ist darin anders als das, was jetzt im System steht?

„Im System“ ist die Belegung, wie der Zimmerplan sie zeigt: der bisherige Gebäudeplan plus die eigene Planung
(geplant/belegt, Mieter, Einpflegen aus der Assistenz) plus Umzüge. Verglichen werden nur Belegungen, die heute oder
später noch laufen.

Unterschiede (je Person und Zimmer):

* **zimmer**   – die Person steht im neuen Gebäudeplan in einem anderen Zimmer
* **zeitraum** – gleiches Zimmer, aber An- oder Abreise weicht um mehr als ``TOLERANZ`` Tage ab
* **fehlt**    – im System, aber nicht (mehr) im neuen Gebäudeplan (geplante künftige Anreisen nicht: die stehen im
  Belegungssystem meist noch nicht)
* **neu**      – im neuen Gebäudeplan, im System noch nicht
* **konflikt** – unsere Planung hat jemanden in einem Zimmer, das laut neuem Gebäudeplan voll (oder gesperrt) ist
* **sperre** / **freigabe** – Sperrung bzw. Zimmerfreigabe ist neu, entfällt oder hat einen anderen Zeitraum
  (verglichen mit dem bisherigen Gebäudeplan; nur zur Information, der neue Plan gilt)

„Eigener Eintrag“ heißt: im Programm geplant (Zuteilen, Assistenz, Mieter) – nicht aus dem Gebäudeplan. Bei
Unterschieden zu eigenen Einträgen entscheidet man, was gelten soll (``optionen_fuer``). ``anwenden`` setzt das um:
``vorrang`` an der Zuweisung („planung“ = eigener Eintrag gilt, auch gegen den Gebäudeplan; „plan“ = der Gebäudeplan
gilt) oder den eigenen Eintrag löschen. Rein, ohne Qt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from . import gebaeudeplan, protokoll, speicher
from . import zimmerplan as zp
from .gebaeudeplan import Belegung

TOLERANZ = timedelta(days=3)        # An-/Abreise im Gebäudeplan weicht oft ein paar Tage ab

ART_TEXT = {"zimmer": "anderes Zimmer", "zeitraum": "anderer Zeitraum", "fehlt": "fehlt im neuen Plan",
            "neu": "neu im Plan", "konflikt": "Doppelbelegung", "sperre": "Sperrung", "freigabe": "Zimmerfreigabe"}
# Auswahl je Unterschied: Schlüssel → Text. Der erste Eintrag ist die Voreinstellung.
WAHL = {   # Schlüssel je Art (Texte mit Zimmer/Zeitraum: ``optionen_fuer``)
    "zimmer": ("plan", "planung"),
    "zeitraum": ("plan", "planung"),
    "fehlt": ("planung", "entfernen"),
    "konflikt": ("planung", "entfernen"),
}
EIGEN = "eigener Eintrag"


def _teile(text: str) -> tuple[str, str]:
    """„2-408 · 26.06.2025 – 30.09.2026 (eigener Eintrag)“ → („2-408“, „26.06.2025 – 30.09.2026“)."""
    zimmer, _, rest = text.partition(" · ")
    return zimmer, rest.split(" (")[0]


def optionen_fuer(u: "Unterschied") -> dict[str, str]:
    """Was nach der Wahl konkret gilt – mit Zimmer und Zeitraum, damit nichts missverständlich ist."""
    s_zi, s_zeit = _teile(u.system)
    p_zi, p_zeit = _teile(u.plan)
    if u.art == "zimmer":
        return {"plan": f"Zimmer {p_zi} aus dem Gebäudeplan übernehmen",
                "planung": f"in Zimmer {s_zi} lassen (eigener Eintrag gilt)"}
    if u.art == "zeitraum":
        return {"plan": f"Zeitraum aus dem Gebäudeplan übernehmen ({p_zeit})",
                "planung": f"eigenen Zeitraum behalten ({s_zeit})"}
    if u.art == "fehlt":
        return {"planung": f"Eintrag in {s_zi} behalten (Belegungssystem nachtragen)",
                "entfernen": f"Eintrag in {s_zi} löschen (wohnt nicht dort)"}
    return {"planung": f"Eintrag in {s_zi} behalten – Doppelbelegung selbst klären",
            "entfernen": f"Eintrag in {s_zi} löschen – Person neu zuteilen"}


@dataclass
class Unterschied:
    art: str
    name: str
    person: str = ""                 # Schlüssel der eigenen Zuweisung ("" = nur Gebäudeplan)
    system: str = ""                 # „2-408 · 26.06.2025 – 30.09.2026 (eigener Eintrag)“
    plan: str = ""                   # wie oben, laut neuem Gebäudeplan
    von: date | None = None
    wahl: str = ""                   # gewählte Option ("" = nur Information)
    optionen: dict = field(default_factory=dict)
    zusatz: str = ""                 # Sperrung/Freigabe: „neu“ | „entfällt“ | „geändert“

    @property
    def entscheidbar(self) -> bool:
        return bool(self.optionen)

    @property
    def art_text(self) -> str:
        return ART_TEXT[self.art] + (f" {self.zusatz}" if self.zusatz else "")

    @property
    def text(self) -> str:
        teile = [f"{self.name}: {self.art_text}"]
        if self.system:
            teile.append(f"im System {self.system}")
        if self.plan:
            teile.append(f"im neuen Plan {self.plan}")
        return " – ".join(teile)


def _kurz(zid: str) -> str:
    return zid.removeprefix("GS-")


def _zeit(von: date, bis: date) -> str:
    return f"{von:%d.%m.%Y} – {bis:%d.%m.%Y}"


def _personen(belegungen, heute: date) -> list[Belegung]:
    return [b for b in belegungen if b.art in ("belegt", "geplant") and b.bis >= heute and b.name
            and b.name != zp.PIVOT_NAME and not zp.name_fehlt(b.name)]


def _gleich(a: str, b: str) -> bool:
    """Gleicher Name: die Wörter des einen stecken ganz im anderen („Beispiel, Kai“ ~ „Beispiel, Kai Leon“)."""
    wa, wb = zp._namenswoerter(a), zp._namenswoerter(b)
    return bool(wa and wb) and (wa <= wb or wb <= wa)


def _spannen(belegungen: list[Belegung]) -> dict[tuple[str, str], tuple[date, date, Belegung]]:
    """(Name, Zimmer) → (frühester Beginn, spätestes Ende, eine Belegung) – Teile um eine Zimmerfreigabe zusammen."""
    erg: dict[tuple[str, str], tuple[date, date, Belegung]] = {}
    for b in belegungen:
        k = (b.person or b.name.strip().lower(), b.zimmer)
        if k in erg:
            von, bis, x = erg[k]
            erg[k] = (min(von, b.von), max(bis, b.bis), x)
        else:
            erg[k] = (b.von, b.bis, b)
    return erg


def _ueberschneidet(v1: date, b1: date, v2: date, b2: date) -> bool:
    return v1 <= b2 + TOLERANZ and v2 - TOLERANZ <= b1


def vergleichen(neu: gebaeudeplan.Gebaeudeplan, stand: zp.Planstand, heute: date | None = None) -> list[Unterschied]:
    """Unterschiede zwischen dem neuen Gebäudeplan und der Belegung im System (Gebäudeplan bisher + Planung)."""
    heute = heute or date.today()
    zuweisung = {z["person"]: z for z in stand.zuweisungen}
    system = _spannen(_personen((b for bs in stand.lage.belegungen.values() for b in bs), heute))
    plan = _spannen(_personen(neu.belegungen, heute))
    erg: list[Unterschied] = []
    gefunden: set[tuple[str, str]] = set()

    for (_k, zid), (von, bis, b) in sorted(system.items(), key=lambda x: (x[1][0], x[1][2].name)):
        eigen = b.person in zuweisung
        quelle = EIGEN if eigen else "Gebäudeplan bisher"
        sys_text = f"{_kurz(zid)} · {_zeit(von, bis)} ({quelle})"
        treffer = [(k, v) for k, v in plan.items() if _gleich(b.name, v[2].name)]
        passend = [(k, v) for k, v in treffer if _ueberschneidet(von, bis, v[0], v[1])]
        hier = [(k, v) for k, v in passend if k[1] == zid]
        if hier:
            k, (p_von, p_bis, _p) = hier[0]
            gefunden.add(k)
            if abs((p_von - von).days) > TOLERANZ.days or abs((p_bis - bis).days) > TOLERANZ.days:
                erg.append(Unterschied("zeitraum", b.name, b.person if eigen else "", sys_text,
                                       f"{_kurz(zid)} · {_zeit(p_von, p_bis)}", von))
            continue
        if passend or treffer:
            k, (p_von, p_bis, _p) = (passend or treffer)[0]
            gefunden.add(k)
            art = "zimmer" if k[1] != zid else "zeitraum"
            erg.append(Unterschied(art, b.name, b.person if eigen else "", sys_text,
                                   f"{_kurz(k[1])} · {_zeit(p_von, p_bis)}", von))
            continue
        if eigen and von > heute and zuweisung[b.person].get("status") != "belegt":
            continue        # geplante Anreise: steht im Belegungssystem meist noch nicht – normal, kein Unterschied
        erg.append(Unterschied("fehlt", b.name, b.person if eigen else "", sys_text, "", von))

    for k, (p_von, p_bis, p) in sorted(plan.items(), key=lambda x: (x[1][0], x[1][2].name)):
        if k not in gefunden:
            erg.append(Unterschied("neu", p.name, "", "", f"{_kurz(k[1])} · {_zeit(p_von, p_bis)}", p_von))

    # Doppelbelegung: Zimmer laut neuem Plan voll oder gesperrt, unsere Planung hat dort jemand anderen
    betten = {z.id: max(z.betten, 1) for z in stand.zimmer}
    im_plan: dict[str, list[Belegung]] = {}
    for b in neu.belegungen:
        if b.art in ("belegt", "gesperrt") and b.bis >= heute:
            im_plan.setdefault(b.zimmer, []).append(b)
    schon = {(u.person, u.art) for u in erg}
    for z in stand.zuweisungen:
        von, bis = date.fromisoformat(z["von"]), date.fromisoformat(z["bis"])
        if bis < heute or (z["person"], "zimmer") in schon:
            continue
        andere = [b for b in im_plan.get(z["zimmer"], []) if b.von <= bis and von <= b.bis
                  and not (b.name and _gleich(b.name, z["name"]))]
        if any(b.art == "gesperrt" for b in andere) or len(andere) >= betten.get(z["zimmer"], 1):
            wer = ", ".join(sorted({(f"gesperrt ({b.grund})" if b.grund else "gesperrt") if b.art == "gesperrt"
                                    else b.name for b in andere}))
            erg.append(Unterschied("konflikt", z["name"], z["person"], f"{_kurz(z['zimmer'])} · {_zeit(von, bis)} "
                                   f"({EIGEN})", f"{_kurz(z['zimmer'])} belegt: {wer}", von))

    alt = stand.plan.belegungen if stand.plan else []
    for art in ("gesperrt", "freigabe"):
        erg += _zeitraeume_vergleichen(art, alt, neu.belegungen, heute)

    for u in erg:                       # nur Unterschiede zur eigenen Planung lassen sich entscheiden
        if u.person and u.art in WAHL:
            u.optionen = optionen_fuer(u)
            frueher = zuweisung.get(u.person, {}).get("vorrang")   # beim letzten Abgleich so entschieden
            u.wahl = frueher if frueher in u.optionen else next(iter(u.optionen))
    reihenfolge = {"konflikt": 0, "zimmer": 1, "zeitraum": 2, "fehlt": 3, "sperre": 4, "freigabe": 5, "neu": 6}
    return sorted(erg, key=lambda u: (reihenfolge[u.art], not u.entscheidbar, u.von or heute, u.name))


def _zeitraeume_vergleichen(art: str, alt: list[Belegung], neu: list[Belegung], heute: date) -> list[Unterschied]:
    """Sperrungen bzw. Zimmerfreigaben je Zimmer: neu, entfällt oder anderer Zeitraum (über ``TOLERANZ``)."""
    def je_zimmer(bel: list[Belegung]) -> dict[str, list[Belegung]]:
        erg: dict[str, list[Belegung]] = {}
        for b in bel:
            if b.art == art and b.bis >= heute:
                erg.setdefault(b.zimmer, []).append(b)
        return erg

    a, n = je_zimmer(alt), je_zimmer(neu)
    typ = "sperre" if art == "gesperrt" else "freigabe"
    erg: list[Unterschied] = []

    def text(b: Belegung) -> str:
        return f"{_kurz(b.zimmer)} · {_zeit(b.von, b.bis)}" + (f" ({b.grund})" if b.grund and art == "gesperrt" else "")

    for zid in sorted(set(a) | set(n)):
        offen_alt = list(a.get(zid, []))
        for b in sorted(n.get(zid, []), key=lambda x: x.von):
            gleich = next((x for x in offen_alt if abs((x.von - b.von).days) <= TOLERANZ.days
                           and abs((x.bis - b.bis).days) <= TOLERANZ.days), None)
            if gleich is not None:
                offen_alt.remove(gleich)
                continue
            ueber = next((x for x in offen_alt if x.von <= b.bis and b.von <= x.bis), None)
            if ueber is not None:
                offen_alt.remove(ueber)
                erg.append(Unterschied(typ, f"Zimmer {_kurz(zid)}", "", text(ueber), text(b), b.von, zusatz="geändert"))
            else:
                erg.append(Unterschied(typ, f"Zimmer {_kurz(zid)}", "", "–", text(b), b.von, zusatz="neu"))
        for x in offen_alt:
            erg.append(Unterschied(typ, f"Zimmer {_kurz(zid)}", "", text(x), "aufgehoben", x.von, zusatz="entfällt"))
    return erg


def zusammenfassung(unterschiede: list[Unterschied]) -> str:
    if not unterschiede:
        return "Keine Unterschiede – der neue Gebäudeplan passt zu Belegung und eigenen Einträgen im System."
    zahl: dict[str, int] = {}
    for u in unterschiede:
        zahl[u.art] = zahl.get(u.art, 0) + 1
    return " · ".join(f"{n} × {ART_TEXT[a]}" for a, n in sorted(zahl.items(), key=lambda x: list(ART_TEXT).index(x[0])))


def anwenden(neu: gebaeudeplan.Gebaeudeplan, unterschiede: list[Unterschied], quelle: dict | None = None) -> int:
    """Gebäudeplan speichern und die Entscheidungen umsetzen. Gibt die Zahl der geänderten Zuweisungen zurück."""
    alle = zp.zuweisungen_laden()
    nach_person = {z["person"]: z for z in alle}
    entfernen: set[str] = set()
    log, n = [], 0
    for u in unterschiede:
        z = nach_person.get(u.person)
        if not u.entscheidbar or z is None:
            continue
        if u.wahl == "entfernen":
            entfernen.add(u.person)
        elif u.art in ("zimmer", "zeitraum") and u.wahl in ("plan", "planung") and z.get("vorrang") != u.wahl:
            z["vorrang"] = u.wahl
            n += 1
            log.append({"aktion": "gilt: " + (EIGEN if u.wahl == "planung" else "Gebäudeplan"), "name": z["name"],
                        "person": u.person, "alt": z["zimmer"], "neu": z["zimmer"], "von": z["von"],
                        "quelle": "Gebäudeplan-Abgleich"})
    log += [{"aktion": "entfernt", "name": nach_person[p]["name"], "person": p, "alt": nach_person[p]["zimmer"],
             "neu": "", "von": nach_person[p]["von"], "quelle": "Gebäudeplan-Abgleich"} for p in entfernen]
    gebaeudeplan.speichern(neu, quelle)
    speicher.schreiben(zp.ZUWEISUNGEN, {"zuweisungen": [z for z in alle if z["person"] not in entfernen]})
    protokoll.eintragen(log)
    return n + len(entfernen)
