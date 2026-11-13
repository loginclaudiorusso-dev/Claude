"""Mail-Erkennung nachgeschärft (1.04). Rein, ohne Oberfläche.

Die Erkennung des Hauptprogramms (``belegung.mails.erkennen``) bleibt unverändert; hier wird ihr Ergebnis ergänzt,
wo sie typische Mails des Internatsdiensts nicht ganz versteht:

* **Zeitraum mit Gedankenstrich:** „vom 08.02. – 26.02.2027“, „8.2.–26.2.27“, „08.02. bis 26.02.2027“ → von/bis (das
  Jahr kommt vom Enddatum).
* **„Zusätzliche Unterbringung“, „Internatsplatz“, „Zimmer anfragen“ …** → Art „Anmeldung“ statt „Hinweis“ (sonst
  zählte nur das erste Datum).
* **Name aus dem Betreff:** „UWTler Muster, Max (123456)“ → „Muster, Max“ (bisher nur „für Vorname Nachname“).
* **Gruppe UWT:** „UWT“, „UWTler“, „Umschüler“ → Maßnahme „UWT“.
* **„Anreise am Sonntag“:** liegt der Beginn nicht auf einem Sonntag, zählt der Sonntag davor als Anreise.
* **„… bestätigen?“** gilt als Bitte um Bestätigung.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date, timedelta

from belegung import mails

_G = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß\-]+"
_BEREICH = re.compile(r"(?<![\d.])(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?\s*(?:–|—|-|bis(?:\s+(?:zum|einschließlich))?)\s*"
                      r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4}|\d{2})?(?![\d])")
_UNTERBRINGUNG = re.compile(r"unterbringung|internatsplatz|zimmer\s*(?:anfrage|reservier|benötig|gebraucht)|"
                            r"(?:benötigt|braucht)\s+(?:ein\s+)?zimmer|unterkunft", re.I)
_UWT = re.compile(r"\bUWT(?:ler(?:in)?)?\b|umsch[üu]l(?:er|erin|ung)", re.I)
_NAME_WORT_NICHT = {"hallo", "liebe", "lieber", "sehr", "guten", "zusätzliche", "zusaetzliche", "unterbringung",
                    "anfrage", "anmeldung", "uwtler", "uwt", "aw", "wg", "re", "fw", "betreff"}
_TAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def _bereinigt(betreff: str) -> str:
    return re.sub(r"^\s*((AW|WG|RE|FW|Fwd?)\s*:\s*)+", "", betreff or "", flags=re.I)


def zeitraum(text: str, heute: date) -> tuple[date, date] | None:
    """Erster Bereich „TT.MM.(JJ) – TT.MM.(JJ)“ im Text; Jahr vom Enddatum, sonst wie im Hauptprogramm ergänzt."""
    for m in _BEREICH.finditer(text or ""):
        j1 = int(m.group(3)) if m.group(3) else None
        j2 = int(m.group(6)) if m.group(6) else None
        bis = mails._jahr(int(m.group(4)), int(m.group(5)), j2 if j2 is not None else j1, heute)
        if not bis:
            continue
        von = mails._jahr(int(m.group(1)), int(m.group(2)), j1 if j1 is not None else bis.year, heute)
        if von and von > bis and j1 is None:
            von = mails._jahr(int(m.group(1)), int(m.group(2)), bis.year - 1, heute)
        if von and von <= bis:
            return von, bis
    return None


def name_aus(text: str) -> str:
    """„Nachname, Vorname“ irgendwo im Text (z. B. Betreff „UWTler Muster, Max (123456)“)."""
    for m in re.finditer(rf"({_G}),\s*({_G})\b", text or ""):
        n, v = m.group(1), m.group(2)
        if n.lower() in _NAME_WORT_NICHT or v.lower() in _NAME_WORT_NICHT or n.lower() in mails._KEIN_NAME:
            continue
        titel = lambda w: w if not w.isupper() else w.capitalize()     # noqa: E731
        return f"{titel(n)}, {titel(v)}"
    return ""


def erkennen(betreff: str, text: str, heute: date | None = None):
    heute = heute or date.today()
    e = mails.erkennen(betreff, text, heute)
    b = _bereinigt(betreff)
    koerper = mails._koerper(text or "")
    alles = f"{b}\n{koerper}"
    klein = alles.lower()
    neu = {}
    unterbringung = bool(_UNTERBRINGUNG.search(alles))
    if e.art in ("hinweis", "unklar") and unterbringung:
        neu["art"] = "anmeldung"
    art = neu.get("art", e.art)
    if not e.name:
        n = name_aus(b) or name_aus(koerper)
        if n:
            neu["name"] = n
    uwt = bool(_UWT.search(alles))
    if uwt and not e.massnahme:
        neu["massnahme"] = "UWT"
    von, bis = e.von, e.bis
    if art in ("anmeldung", "gast", "storno"):
        zr = zeitraum(alles, heute)
        if zr and (bis is None or von is None or (von, bis) != zr):
            if bis is None or von is None or not (zr[0] <= von <= bis <= zr[1]):
                von, bis = zr
    anreise_so = bool(re.search(r"anreise\s+(?:am\s+)?sonntag", klein))
    beginn = von
    if von and anreise_so and von.weekday() != 6:
        von = von - timedelta(days=von.weekday() + 1)       # der Sonntag davor
    if (von, bis) != (e.von, e.bis):
        neu["von"], neu["bis"] = von, bis
    if not e.bestaetigung and re.search(r"bestätigen\b|bestaetigen\b", klein):
        neu["bestaetigung"] = True
    if not neu:
        return e
    e2 = replace(e, **neu)
    # Zusammenfassung neu, wenn sich Art oder Zeitraum geändert haben
    if "art" in neu or "von" in neu:
        teile = []
        if art == "anmeldung":
            was = "Zusätzliche Unterbringung" if re.search(r"zusätzlich|zusaetzlich", klein) else "Unterbringung"
            teile.append(was + (" (UWT)" if uwt else ""))
            if beginn and bis:
                teile[-1] += f" {beginn:%d.%m.}–{bis:%d.%m.%Y}"
            if anreise_so and von:
                teile.append(f"Anreise {_TAGE[von.weekday()]} {von:%d.%m.%Y}")
            if re.search(r"nahtlos|anschließend|direkt\s+im\s+anschluss", klein):
                teile.append("nahtlos im Anschluss")
        if e2.bestaetigung:
            teile.append("Bestätigung erbeten")
        if e2.kostenuebernahme:
            teile.append("Kostenübernahme folgt")
        e2.zusammenfassung = " · ".join(teile) or e.zusammenfassung
    # „unsicher“ neu bewerten
    u = [x for x in e.unsicher if not (x.startswith("Keine Person") and (e2.name or e2.tn_id))
         and not (x.startswith("Zeitraum unvollständig") and e2.von and e2.bis)
         and not (x.startswith("Art der Mail") and e2.art != "unklar")]
    if e2.art in ("gast", "anmeldung") and not (e2.von and e2.bis) and not any(x.startswith("Zeitraum") for x in u):
        u.append("Zeitraum unvollständig – bitte Anreise und Abreise prüfen.")
    if anreise_so and beginn and von != beginn:
        u.append(f"Anreise am Sonntag: Zimmer ab {von:%d.%m.%Y} eingeplant (Unterbringung ab {beginn:%d.%m.}) – bitte prüfen.")
    e2.unsicher = u
    return e2
