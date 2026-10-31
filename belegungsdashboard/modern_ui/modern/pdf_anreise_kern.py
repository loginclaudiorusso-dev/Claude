"""Anreiselisten als PDF („Teilnehmer Beginn“ aus der Teilnehmerverwaltung) – so kommen sie in Bad Pyrmont und
Weser-Ems.

Aufbau (je Maßnahme ein Block, nach Beginn sortiert)::

    BP KBM 2611                vom 03.11.2026 bis 02.11.2028        ← Maßnahme und Zeitraum
      03.11.26  Name, Vorname   TT.MM.JJ  DRV Bund        P K       ← Eintritt (* = verspäteter Einstieg), Name,
                                                                       (Geburtsdatum), Kostenträger, Kennzeichen
                                          Braunschweig-Hannover: H  ← Zusatz zum Kostenträger (ignoriert)
                                          Maßnahme BP KBM 2611: 4 TN

* **K** = wohnt im Internat, ohne K kein Zimmer.
* **Anreise** = Eintrittsdatum der Person (auch bei verspätetem Einstieg), **Abreise** = Ende der Maßnahme.
* Das Geburtsdatum wird nicht übernommen (Datensparsamkeit), der Kostenträger auch nicht.
* Die Liste hat keine TN-ID: Personen werden über Name und Anreisetag wiedererkannt. Deshalb nicht mit den
  Excel-Listen mischen, die über die TN-ID gehen (Goslar bleibt bei Excel).

Rein, ohne NiceGUI.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from belegung import anreiseliste

_MASSNAHME = re.compile(r"^\s*((?:BP|WE|GS)\s+\S.*?)\s{2,}vom\s+(\d{2}\.\d{2}\.\d{4})\s+bis\s+(\d{2}\.\d{2}\.\d{4})\s*$")
_PERSON = re.compile(r"^\s*(\d{2}\.\d{2}\.\d{2})(\*?)\s+(\S.*?,\s*\S.*?)\s{2,}\d{2}\.\d{2}\.\d{2}\b(.*)$")
_KOPF = re.compile(r"Teilnehmer\s+Beginn")


def _d(text: str, fmt: str) -> date:
    return datetime.strptime(text, fmt).date()


def text_lesen(pfad: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:                    # pragma: no cover – pypdf gehört zu den Paketen
        raise ValueError("Zum Lesen von PDFs wird das Paket „pypdf“ benötigt.") from exc
    seiten = PdfReader(str(pfad)).pages
    return "\n".join(s.extract_text(extraction_mode="layout") or "" for s in seiten)


def ist_liste(text: str) -> bool:
    return bool(_KOPF.search(text)) or any(_MASSNAHME.match(z) for z in text.splitlines())


def lesen_text(text: str, datei: str) -> list[anreiseliste.Anreiseliste]:
    """Text der PDF → je Maßnahme und Anreisetag eine Anreiseliste (wie die Excel-Listen)."""
    listen: dict[tuple[date, str], anreiseliste.Anreiseliste] = {}
    massnahme, ende = None, None
    for zeile in text.splitlines():
        if m := _MASSNAHME.match(zeile):
            massnahme = re.sub(r"\s+", " ", m.group(1)).strip()
            ende = _d(m.group(3), "%d.%m.%Y")
            continue
        m = _PERSON.match(zeile)
        if not m or massnahme is None:
            continue
        anreise = _d(m.group(1), "%d.%m.%y")
        name = re.sub(r"\s+", " ", m.group(3)).strip()
        rest = m.group(4).split()
        kennzeichen = set()
        while rest and rest[-1] in ("K", "P"):
            kennzeichen.add(rest.pop())
        gruppe = "EMR" if "EMR" in massnahme.upper() else "Reha"
        p = anreiseliste.Person(name=name, massnahme=massnahme, anreise=anreise, internat="K" in kennzeichen,
                                gruppe=gruppe, abreise=ende if ende and ende >= anreise else None,
                                bemerkung="verspäteter Einstieg" if m.group(2) else "")
        liste = listen.setdefault((anreise, massnahme), anreiseliste.Anreiseliste(datei, anreise, massnahme, []))
        p.liste = liste.schluessel
        liste.personen.append(p)
    return sorted(listen.values(), key=lambda l: (l.datum, l.gruppe))


def lesen(pfad: Path, datei: str) -> list[anreiseliste.Anreiseliste]:
    text = text_lesen(pfad)
    listen = lesen_text(text, datei)
    if not listen:
        raise ValueError(f"{datei}: keine Maßnahmen mit Teilnehmenden erkannt – ist das die Liste „Teilnehmer Beginn“?")
    return listen
