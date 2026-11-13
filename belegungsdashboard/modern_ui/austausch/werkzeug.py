"""Austausch für das alte Programm (1.05) – Export und Einlesen direkt im Datenordner des alten Programms.

Ohne Oberfläche (die steht in ``austausch_alt.py``), damit es sich testen lässt. Vor jedem Einlesen werden die
betroffenen Dateien nach ``Sicherungen/austausch_<Zeit>/`` kopiert. Das alte Programm selbst wird nicht verändert.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
PROGRAMM_ORDNER = HIER.parent.parent                    # …/belegungsdashboard (dort liegt das alte Programm)
for p in (PROGRAMM_ORDNER, HIER.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from belegung import konfig, speicher  # noqa: E402

from modern import austausch_kern as ak  # noqa: E402

PROGRAMM = "alt"


def datenordner() -> Path:
    return konfig.datenordner()


def _lesen(ordner: Path):
    return lambda name, standard: speicher.lesen(name, standard, ordner)


def _schreiben(ordner: Path):
    return lambda name, daten: speicher.schreiben(name, daten, ordner)


def export(ordner: Path, alles: bool = False) -> tuple[bytes, str, int, dict]:
    st = ak.stand(_lesen(ordner))
    liste = ak.aenderungen(st, None if alles else ak.basis_lesen(_lesen(ordner)))
    inhalt = ak.datei_bauen(liste, PROGRAMM)
    return json.dumps(inhalt, ensure_ascii=False, indent=1).encode("utf-8"), ak.dateiname(PROGRAMM), len(liste), st


def export_gemerkt(ordner: Path, st: dict) -> None:
    ak.basis_schreiben(_schreiben(ordner), ak.pruefwerte(st))


def pruefen(ordner: Path, daten: bytes) -> tuple[list[ak.Punkt], dict]:
    try:
        inhalt = json.loads(daten.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ak.AustauschFehler("Die Datei lässt sich nicht lesen – ist es eine INNternat-Austauschdatei?") from exc
    liste = ak.datei_pruefen(inhalt)
    return ak.abgleichen(liste, ak.stand(_lesen(ordner))), {k: inhalt.get(k) for k in ("von", "erstellt", "programm")}


def uebernehmen(ordner: Path, punkte: list[ak.Punkt], jetzt: datetime | None = None) -> tuple[dict, Path]:
    """Sichert die Dateien, schreibt die gewählten Punkte und die neue Basis. Rückgabe: (Anzahl, Sicherungsordner)."""
    jetzt = jetzt or datetime.now()
    sicherung = ordner / "Sicherungen" / f"austausch_{jetzt:%Y-%m-%d_%H%M%S}"
    for name in [b.datei for b in ak.BEREICHE] + [ak.BASIS_DATEI]:
        quelle = ordner / name
        if quelle.exists():
            ziel = sicherung / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(quelle, ziel)
    zahl = ak.anwenden(punkte, _lesen(ordner), _schreiben(ordner))
    ak.basis_schreiben(_schreiben(ordner), ak.basis_nach_import(ak.basis_lesen(_lesen(ordner)), punkte))
    return zahl, sicherung
