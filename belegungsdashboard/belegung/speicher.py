"""Kleine JSON-Ablage neben der exe.

Dateinamen der Vorversion (manuelle_eintraege.json, kapazitaeten_manuell.json,
pivot_profile.json) bleiben gleich, damit bestehende Installationen ihre Daten behalten.
Geschrieben wird atomar (temp + replace), damit ein Absturz keine halbe Datei hinterlässt.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from .konfig import datenordner

log = logging.getLogger(__name__)

EINSTELLUNGEN = "einstellungen.json"
MANUELLE_EINTRAEGE = "manuelle_eintraege.json"
KAPAZITAETEN = "kapazitaeten_manuell.json"
PIVOT_PROFILE = "pivot_profile.json"
IMPORT_ORDNER = "importe"


def pfad(name: str, ordner: Path | None = None) -> Path:
    return (ordner or datenordner()) / name


def lesen(name: str, standard: Any, ordner: Path | None = None) -> Any:
    p = pfad(name, ordner)
    if not p.exists():
        return standard
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("%s konnte nicht gelesen werden (%s) – verwende Standardwerte.", p.name, exc)
        return standard


def schreiben(name: str, daten: Any, ordner: Path | None = None) -> None:
    p = pfad(name, ordner)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=p.name, suffix=".tmp", dir=p.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(daten, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, p)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def einstellungen() -> dict:
    return lesen(EINSTELLUNGEN, {})


def einstellung_setzen(schluessel: str, wert: Any) -> None:
    daten = einstellungen()
    daten[schluessel] = wert
    schreiben(EINSTELLUNGEN, daten)
