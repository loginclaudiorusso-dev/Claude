"""Automatische Datensicherung der Arbeitsdaten (Zuweisungen, Termine, Notizen, Importe, Einstellungen …).

Gesichert werden alle JSON-Dateien im Datenordner und im Unterordner ``importe`` – also alles, was das
Programm selbst schreibt. Mitgelieferte bzw. abgelegte Quelldateien (Gebäudeplan-Word, UWT-Listen, Excel)
bleiben, wo sie sind, und werden nicht verändert.

* Beim Start einmal am Tag und immer bei einer neuen Programmversion (vor dem ersten Schreiben).
* Ablage: ``Sicherungen/<Datum>_<Uhrzeit>_v<Version>_<Anlass>/`` im Datenordner; die neuesten
  ``BEHALTEN`` Sicherungen bleiben, ältere werden entfernt.
* Wiederherstellen sichert vorher den aktuellen Stand („vor Wiederherstellung“) – nichts geht verloren.

API-Schlüssel liegen in der Windows-Anmeldeinformationsverwaltung, nicht in diesen Dateien.
Rein, ohne Qt.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import __version__
from .konfig import datenordner

ORDNER = "Sicherungen"
BEHALTEN = 30
_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{6})_v([\w.]+)_(.+)$")


@dataclass
class Sicherung:
    pfad: Path
    zeit: datetime
    version: str
    anlass: str
    dateien: int

    @property
    def text(self) -> str:
        return f"{self.zeit:%d.%m.%Y %H:%M} · v{self.version} · {self.anlass} · {self.dateien} Dateien"


def _daten(ordner: Path) -> list[Path]:
    """Alle vom Programm geschriebenen Dateien (relativ zum Datenordner)."""
    dateien = [p for p in ordner.glob("*.json") if p.is_file()]
    dateien += [p for p in (ordner / "importe").glob("*.json") if p.is_file()]
    return sorted(p.relative_to(ordner) for p in dateien)


def liste(ordner: Path | None = None) -> list[Sicherung]:
    """Vorhandene Sicherungen, neueste zuerst."""
    basis = (ordner or datenordner()) / ORDNER
    ergebnis = []
    for p in basis.glob("*") if basis.exists() else []:
        m = _NAME.match(p.name)
        if not p.is_dir() or not m:
            continue
        zeit = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H%M%S")
        ergebnis.append(Sicherung(p, zeit, m.group(3), m.group(4).replace("-", " "),
                                  sum(1 for x in p.rglob("*.json"))))
    return sorted(ergebnis, key=lambda s: s.zeit, reverse=True)


def sichern(anlass: str = "manuell", ordner: Path | None = None, jetzt: datetime | None = None,
            raeumen: bool = True) -> Sicherung | None:
    """Kopiert die Arbeitsdaten in einen neuen Sicherungsordner. None, wenn es (noch) nichts zu sichern gibt."""
    ordner = ordner or datenordner()
    dateien = _daten(ordner)
    if not dateien:
        return None
    jetzt = jetzt or datetime.now()
    name = f"{jetzt:%Y-%m-%d_%H%M%S}_v{__version__}_{re.sub(r'[^A-Za-z0-9ÄÖÜäöüß]+', '-', anlass).strip('-')}"
    ziel = ordner / ORDNER / name
    n = 0
    while ziel.exists():                       # zwei Sicherungen in derselben Sekunde
        n += 1
        ziel = ordner / ORDNER / f"{name}-{n}"
    for rel in dateien:
        (ziel / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ordner / rel, ziel / rel)
    if raeumen:
        aufraeumen(ordner)
    return next(s for s in liste(ordner) if s.pfad == ziel)


def aufraeumen(ordner: Path | None = None, behalten: int = BEHALTEN) -> None:
    for s in liste(ordner)[behalten:]:
        shutil.rmtree(s.pfad, ignore_errors=True)


def beim_start(ordner: Path | None = None, jetzt: datetime | None = None) -> Sicherung | None:
    """Einmal am Tag und bei jeder neuen Programmversion sichern."""
    jetzt = jetzt or datetime.now()
    vorhanden = liste(ordner)
    if vorhanden and vorhanden[0].zeit.date() == jetzt.date() and any(s.version == __version__ for s in vorhanden):
        return None
    neu = not any(s.version == __version__ for s in vorhanden)
    return sichern("vor Update" if neu and vorhanden else "Start", ordner, jetzt)


def wiederherstellen(sicherung: Sicherung, ordner: Path | None = None) -> Sicherung | None:
    """Stellt die Arbeitsdaten einer Sicherung wieder her. Der aktuelle Stand wird vorher gesichert.
    Dateien, die es in der Sicherung nicht gibt (z. B. neu hinzugekommene), bleiben unverändert."""
    ordner = ordner or datenordner()
    vorher = sichern("vor Wiederherstellung", ordner, raeumen=False)   # Quelle nicht wegräumen
    for quelle in sorted(sicherung.pfad.rglob("*.json")):
        rel = quelle.relative_to(sicherung.pfad)
        (ordner / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle, ordner / rel)
    aufraeumen(ordner)
    return vorher
