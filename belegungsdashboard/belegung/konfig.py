"""Zentrale Konstanten und Pfade."""

from __future__ import annotations

import re
import sys
from pathlib import Path

STANDORTE = ["BFW BP", "BFW GS", "BFW WE"]
GESAMT = "Gesamt"
STANDORT_LABEL = {"BFW BP": "Bad Pyrmont", "BFW GS": "Goslar", "BFW WE": "Weser-Ems", GESAMT: "Gesamt"}
STANDORT_KURZ = {"BFW BP": "BP", "BFW GS": "GS", "BFW WE": "WE", GESAMT: "Σ"}

# Leerer Standort bei Mietern/Gästen => Goslar (Regel aus der alten Excel-Lösung).
STANDARD_STANDORT_MIETER = "BFW GS"

EXCEL_BEVORZUGTER_NAME = "pivot_neu.xlsx"

# Ampel-Schwellen für die Auslastung (Anteil an der Kapazität) – Werte der Vorversion.
AMPEL_GELB = 0.70
AMPEL_ROT = 0.85


def ampel_stufe(anteil: float | None) -> tuple[str, str]:
    """(Stufe, Klartext) für einen Auslastungsanteil. Stufe: ok | knapp | kritisch | ueber | unbekannt."""
    if anteil is None:
        return "unbekannt", "keine Kapazität hinterlegt"
    if anteil > 1.0:
        return "ueber", "über Kapazität"
    if anteil >= AMPEL_ROT:
        return "kritisch", "kaum Reserve"
    if anteil >= AMPEL_GELB:
        return "knapp", "wird knapp"
    return "ok", "Reserve vorhanden"

# Kategorien der Belegung. "Reha" kommt aus der Pivot, alles andere aus Listen.
KATEGORIEN_NETTO = ["Reha", "DRK", "Landkreis", "UWT", "Pflegeschule", "Mieter", "Gäste"]
KATEGORIEN_BRUTTO_ZUSATZ = ["FRAI", "Jugendhilfe"]
KATEGORIE_ANREISE = "Anreise"
KATEGORIE_ANDERE = "andere Bereiche"
MANUELLE_KATEGORIEN = ["Mieter", "Gäste", "DRK", "Landkreis", "UWT", "Pflegeschule", "FRAI", "Jugendhilfe"]

_STANDORT_ALIASE: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(bfw\s*)?bp\b|pyrmont", re.I), "BFW BP"),
    (re.compile(r"\b(bfw\s*)?gs\b|goslar", re.I), "BFW GS"),
    (re.compile(r"\b(bfw\s*)?we\b|weser[\s-]*ems", re.I), "BFW WE"),
]


def standort_normalisieren(text: object) -> str | None:
    """'Bad Pyrmont', 'BP', 'bfw bp' -> 'BFW BP'. None, wenn nichts erkannt wird."""
    if text is None:
        return None
    t = str(text).strip()
    if not t:
        return None
    if t in STANDORTE:
        return t
    for muster, standort in _STANDORT_ALIASE:
        if muster.search(t):
            return standort
    return None


def programmordner() -> Path:
    """Ordner der .exe (PyInstaller) bzw. des Startskripts."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def datenordner() -> Path:
    """Ablage für Einstellungen und lokale Listen (Standard: neben der exe).
    Mit der Umgebungsvariable BELEGUNG_DATEN umlenkbar, z. B. für Tests oder ein Netzlaufwerk."""
    import os

    ziel = os.environ.get("BELEGUNG_DATEN")
    return Path(ziel) if ziel else programmordner()


def ressourcenordner() -> Path:
    """Ordner mit mitgelieferten Dateien (bei --onefile das Entpackverzeichnis)."""
    return Path(getattr(sys, "_MEIPASS", programmordner()))
