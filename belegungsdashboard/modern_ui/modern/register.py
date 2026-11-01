"""Gliederung der neuen Oberfläche: eine Ebene in der Seitenleiste, Unteransichten als Umschalter im Kopf."""

from __future__ import annotations

from . import (seite_auswertung, seite_daten, seite_einstellungen, seite_heute, seite_inventar, seite_termine,
               seite_zimmer, seiten)
from . import seite_assistenz, seite_steuerung

# (Schlüssel, Titel, Symbol, Gruppe)
NAV = [
    ("heute", "Heute", "today", ""),
    ("anreisen", "Anreisen", "flight_land", "Betrieb"),
    ("zimmer", "Zimmer", "meeting_room", "Betrieb"),
    ("reinigung", "Reinigung", "cleaning_services", "Betrieb"),
    ("termine", "Termine", "event", "Betrieb"),
    ("assistenz", "Assistenz", "auto_awesome", "Betrieb"),
    ("mieter", "Mieter", "key", "Betrieb"),
    ("auswertung", "Auswertung", "insights", "Überblick"),
    ("daten", "Daten & Import", "upload_file", "Verwalten"),
    ("inventar", "Inventar", "inventory_2", "Verwalten"),
    ("einstellungen", "Einstellungen", "settings", "Verwalten"),
    ("steuerung", "Steuerung", "query_stats", "Leitung"),     # selten genutzt – ganz unten, abgesetzt
]
TITEL = {k: t for k, t, _i, _g in NAV}

# Schlüssel → (Daten laden – im Hintergrund, Zeichnen). „anreisen“ baut die Oberfläche selbst.
SEITEN = {
    "heute": (seite_heute.daten, seite_heute.zeichnen),
    "zimmer": (seite_zimmer.daten, seite_zimmer.zeichnen),
    "reinigung": (seiten.rg_daten, seiten.rg_zeichnen),
    "termine": (seite_termine.daten, seite_termine.zeichnen),
    "assistenz": (seite_assistenz.daten, seite_assistenz.zeichnen),
    "mieter": (seiten.mt_daten, seiten.mt_zeichnen),
    "auswertung": (seite_auswertung.daten, seite_auswertung.zeichnen),
    "daten": (seite_daten.daten, seite_daten.zeichnen),
    "inventar": (seite_inventar.daten, seite_inventar.zeichnen),
    "einstellungen": (seite_einstellungen.daten, seite_einstellungen.zeichnen),
    "steuerung": (seite_steuerung.daten, seite_steuerung.zeichnen),
}
