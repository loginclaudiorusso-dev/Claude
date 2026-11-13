"""Austauschdatei in der neuen Oberfläche (1.05): Export, Prüfen, Übernehmen – mit Rückgängig (``_schritt``).

Die Regeln stehen in ``austausch_kern`` (rein); hier nur das Lesen und Schreiben im Datenordner.
"""

from __future__ import annotations

import json

from belegung import speicher

from . import austausch_kern as ak

PROGRAMM = "neu"


def export(alles: bool = False) -> tuple[bytes, str, int, dict]:
    """(Dateiinhalt, Dateiname, Anzahl Änderungen, Stand). Die Basis wird erst mit ``export_gemerkt`` fortgeschrieben."""
    st = ak.stand(speicher.lesen)
    liste = ak.aenderungen(st, None if alles else ak.basis_lesen(speicher.lesen))
    inhalt = ak.datei_bauen(liste, PROGRAMM)
    roh = json.dumps(inhalt, ensure_ascii=False, indent=1).encode("utf-8")
    return roh, ak.dateiname(PROGRAMM), len(liste), st


def export_gemerkt(st: dict) -> None:
    ak.basis_schreiben(speicher.schreiben, ak.pruefwerte(st))


def lesen(daten: bytes) -> tuple[list[ak.Punkt], dict]:
    """Prüft die Datei und gleicht sie mit dem Stand hier ab. AustauschFehler mit verständlichem Text."""
    try:
        inhalt = json.loads(daten.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ak.AustauschFehler("Die Datei lässt sich nicht lesen – ist es eine INNternat-Austauschdatei?") from exc
    liste = ak.datei_pruefen(inhalt)
    return ak.abgleichen(liste, ak.stand(speicher.lesen)), {k: inhalt.get(k) for k in ("von", "erstellt", "programm", "art")}


def uebernehmen(punkte: list[ak.Punkt]) -> str:
    """Schreibt die gewählten Punkte (alles oder nichts, mit Rückgängig) und schreibt die Basis fort."""
    from .kern import _schritt

    dateien = [b.datei for b in ak.BEREICHE]
    erg: dict = {}

    def aktion():
        erg.update(ak.anwenden(punkte, speicher.lesen, speicher.schreiben))
        ak.basis_schreiben(speicher.schreiben, ak.basis_nach_import(ak.basis_lesen(speicher.lesen), punkte))
    _schritt("Austauschdatei eingelesen", aktion, dateien + [ak.BASIS_DATEI])
    teile = [f"{erg.get('neu', 0)} neu", f"{erg.get('geaendert', 0)} geändert", f"{erg.get('entfernt', 0)} entfernt"]
    return "Austauschdatei übernommen: " + ", ".join(teile)
