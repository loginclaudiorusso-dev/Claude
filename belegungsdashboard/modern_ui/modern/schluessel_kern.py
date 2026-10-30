"""Schlüssellisten abgleichen: die An- und Abreiselisten vom Empfang (Spalten Anreise, Abreise, An, Ab, Zimmer, Name …).

Dort steht, für welches Zimmer der Schlüssel ausgegeben wurde – das ist die Wahrheit. Der Abgleich vergleicht jede Zeile
mit dem, was das Programm zeigt (eigene Planung und Gebäudeplan) und schlägt Korrekturen vor:

* **stimmt** – das Programm zeigt die Person im selben Zimmer.
* **korrigieren** – das Programm zeigt ein anderes Zimmer (oder keins). Übernehmen setzt die eigene Planung auf das
  Schlüssel-Zimmer, als „fest“ und mit Vorrang vor dem Gebäudeplan (wie „Planung stimmt“ beim Klären).
* **nur Gebäudeplan** / **nicht gefunden** – die Person steht nicht in den Anreiselisten; dann im Belegungssystem
  korrigieren (Hinweis, nichts zum Übernehmen).

Personen werden wie im Hauptprogramm über den Namen (alle Wörter) und den Zeitraum (± 3 Tage) erkannt. Nichts wird
ohne Bestätigung geändert; ein Rückgängig für alles. Rein, ohne NiceGUI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from belegung import zimmerplan as zp

TOLERANZ = timedelta(days=3)
_ZIMMER = re.compile(r"(\d(?:\.\d)?)\s*-\s*([A-Za-z]?\d{2,4})")


@dataclass
class Eintrag:
    datei: str
    zeile: int
    anreise: date
    abreise: date | None
    an: bool              # Schlüssel ausgegeben
    ab: bool              # Schlüssel zurück
    zimmer_text: str
    zimmer: str | None    # Zimmer-ID
    name: str
    bemerkung: str = ""


@dataclass
class Punkt:
    e: Eintrag
    art: str              # stimmt | korrigieren | nur_plan | unbekannt | zimmer_unbekannt
    text: str
    person: str = ""      # Schlüssel der Anreise-Person (zum Korrigieren)
    jetzt: str = ""       # Zimmer, das das Programm jetzt zeigt (Kurzform) oder ""
    hinweise: list[str] = field(default_factory=list)

    @property
    def laeuft(self) -> bool:
        return self.e.abreise is None or self.e.abreise >= date.today()


def _datum(v) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    m = re.match(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{2,4})", str(v or ""))
    if not m:
        return None
    j = int(m.group(3))
    return date(j + 2000 if j < 100 else j, int(m.group(2)), int(m.group(1)))


def lesen(pfad: Path, name: str, stand: zp.Planstand) -> list[Eintrag]:
    """Alle Zeilen mit Anreisedatum und Zimmer. Erkennt die Kopfzeile an „Anreise“, „Zimmer“ und „Name“."""
    import openpyxl

    ws = openpyxl.load_workbook(pfad, data_only=True, read_only=True).active
    zeilen = list(ws.iter_rows(values_only=True))
    kopf, spalten = None, {}
    for i, z in enumerate(zeilen[:15]):
        texte = [str(x or "").strip().lower() for x in z]
        if "anreise" in texte and "zimmer" in texte and "name" in texte:
            kopf, spalten = i, {t: j for j, t in enumerate(texte) if t}
            break
    if kopf is None:
        raise ValueError(f"{name}: keine Kopfzeile mit „Anreise“, „Zimmer“ und „Name“ gefunden.")
    def wert(z, t):
        j = spalten.get(t)
        return z[j] if j is not None and j < len(z) else None
    erg = []
    for nr, z in enumerate(zeilen[kopf + 1:], kopf + 2):
        an = _datum(wert(z, "anreise"))
        n = str(wert(z, "name") or "").strip()
        if an is None or not n:
            continue
        zt = str(wert(z, "zimmer") or "").strip()
        m = _ZIMMER.search(zt)
        zid = None
        if m:
            kandidat = f"{m.group(1)}-{m.group(2).upper()}"
            zid = next((x.id for x in stand.zimmer if x.kurz.upper() == kandidat), None)
        erg.append(Eintrag(name, nr, an, _datum(wert(z, "abreise")), str(wert(z, "an") or "").strip().upper() == "X",
                           str(wert(z, "ab") or "").strip().upper() == "X", zt, zid, " ".join(n.split()),
                           str(wert(z, "bemerkung") or "").strip()))
    return erg


def _woerter(name: str) -> frozenset[str]:
    return zp._namenswoerter(name)


def _gleich(a: frozenset, b: frozenset) -> bool:
    return bool(a) and bool(b) and (a <= b or b <= a) and (len(a & b) >= 2 or min(len(a), len(b)) == 1)


def _ueberschneidet(e: Eintrag, von: date, bis: date) -> bool:
    ende = e.abreise or e.anreise
    return von <= ende + TOLERANZ and e.anreise - TOLERANZ <= bis


def vergleichen(stand: zp.Planstand, eintraege: list[Eintrag]) -> list[Punkt]:
    from . import kern

    strittig = {s.person: s for s in kern.strittige(stand)}
    plan = [b for b in (stand.plan.belegungen if stand.plan else []) if b.art == "belegt" and b.name]
    erg = []
    for e in eintraege:
        w = _woerter(e.name)
        if e.zimmer is None:
            erg.append(Punkt(e, "zimmer_unbekannt", f"Zimmer „{e.zimmer_text}“ nicht erkannt – bitte von Hand prüfen."))
            continue
        kurz_ = kern.kurz(e.zimmer)
        person = next((b for b in stand.bedarf if _gleich(w, _woerter(b.name)) and _ueberschneidet(e, b.von, b.bis)), None)
        im_plan = [b for b in plan if _gleich(w, _woerter(b.name)) and _ueberschneidet(e, b.von, b.bis)]
        hinweise = []
        ende = e.abreise or e.anreise
        andere = sorted({zp.anzeige_name(b.name) for b in stand.lage.belegungen.get(e.zimmer, [])
                         if b.art in ("belegt", "geplant") and b.name and b.name != zp.PIVOT_NAME
                         and not _gleich(w, _woerter(b.name)) and b.von <= ende and e.anreise <= b.bis})
        if andere:
            hinweise.append(f"laut Programm im Zeitraum auch in {kurz_}: {', '.join(andere)}")
        if person is None:
            if im_plan:
                gebucht = im_plan[0].zimmer
                if gebucht == e.zimmer:
                    erg.append(Punkt(e, "stimmt", f"stimmt (Gebäudeplan {kurz_})", jetzt=kurz_, hinweise=hinweise))
                else:
                    erg.append(Punkt(e, "nur_plan", f"Gebäudeplan: {kern.kurz(gebucht)} – Schlüssel für {kurz_}. Die Person "
                                     "steht in keiner Anreiseliste: bitte im Belegungssystem umbuchen.",
                                     jetzt=kern.kurz(gebucht), hinweise=hinweise))
            else:
                erg.append(Punkt(e, "unbekannt", "nicht im Programm gefunden (keine Anreiseliste, kein Gebäudeplan).",
                                 hinweise=hinweise))
            continue
        zw = stand.zugewiesen(person.schluessel) or {}
        if person.schluessel in strittig:
            jetzt = strittig[person.schluessel].gebucht
        elif zw.get("zimmer"):
            jetzt = zw["zimmer"]
        else:
            jetzt = im_plan[0].zimmer if im_plan else ""
        if jetzt == e.zimmer and zw.get("zimmer") in (None, e.zimmer):
            erg.append(Punkt(e, "stimmt", f"stimmt ({kurz_})", person.schluessel, kurz_, hinweise))
            continue
        bisher = [f"Planung {kern.kurz(zw['zimmer'])}"] if zw.get("zimmer") else []
        bisher += [f"Gebäudeplan {kern.kurz(b.zimmer)}" for b in im_plan[:1]]
        erg.append(Punkt(e, "korrigieren", f"bisher {' · '.join(bisher) or 'ohne Zimmer'} → Schlüssel für {kurz_}",
                         person.schluessel, kern.kurz(jetzt) if jetzt else "", hinweise))
    return sorted(erg, key=lambda p: (["korrigieren", "nur_plan", "unbekannt", "zimmer_unbekannt", "stimmt"].index(p.art),
                                      p.e.anreise, p.e.name))


def uebernehmen(punkte: list[Punkt]) -> str:
    """Eigene Planung auf das Schlüssel-Zimmer setzen – „fest“ und mit Vorrang vor dem Gebäudeplan. Ein Schritt."""
    from belegung import protokoll, speicher

    from .kern import _schritt, kurz

    stand = zp.laden()
    bedarf = {b.schluessel: b for b in stand.bedarf}
    auswahl = [p for p in punkte if p.art == "korrigieren" and p.person in bedarf and p.e.zimmer]
    if not auswahl:
        raise ValueError("Nichts zum Übernehmen ausgewählt.")

    def aendern():
        alle = zp.zuweisungen_laden()
        nach_person = {z["person"]: z for z in alle}
        jetzt = datetime.now().isoformat(timespec="seconds")
        log = []
        for p in auswahl:
            b = bedarf[p.person]
            z = nach_person.get(p.person)
            if z is None:
                z = {"person": b.schluessel, "name": b.name, "massnahme": b.massnahme, "gruppe": b.gruppe,
                     "geschlecht": b.geschlecht, "von": b.von.isoformat(), "bis": b.bis.isoformat()}
                alle.append(z)
                nach_person[p.person] = z
            alt = z.get("zimmer", "")
            z.update(zimmer=p.e.zimmer, status="belegt", belegt_am=jetzt, vorrang="planung")
            log.append({"aktion": "Schlüsselliste", "name": b.name, "person": b.schluessel, "alt": alt, "neu": p.e.zimmer,
                        "von": b.von.isoformat(), "quelle": f"Schlüsselliste {p.e.datei}"})
        speicher.schreiben(zp.ZUWEISUNGEN, {"zuweisungen": alle})
        protokoll.eintragen(log)
    _schritt(f"Schlüsselliste: {len(auswahl)} Zimmer korrigiert", aendern, [zp.ZUWEISUNGEN])
    return f"{len(auswahl)} Zimmer nach Schlüsselliste korrigiert" + (
        f" (z. B. {bedarf[auswahl[0].person].name} → {kurz(auswahl[0].e.zimmer)})" if len(auswahl) == 1 else "")
