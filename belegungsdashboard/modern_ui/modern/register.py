"""Gliederung der neuen Oberfläche: eine Ebene in der Seitenleiste, Unteransichten als Umschalter im Kopf."""

from __future__ import annotations

from . import (seite_auswertung, seite_daten, seite_einstellungen, seite_heute, seite_inventar, seite_termine,
               seite_zimmer, seiten)
from . import seite_assistenz, seite_steuerung

# (Schlüssel, Titel, Symbol, Bereich) – 1.39: Titel und Bereiche nach Navigation 2.0
NAV = [
    ("heute", "Übersicht", "today", ""),
    ("anreisen", "Anreisen", "flight_land", "Anreisen"),
    ("zimmer", "Zimmer & Haus", "meeting_room", "Zimmer & Haus"),
    ("reinigung", "Reinigung", "cleaning_services", "Zimmer & Haus"),
    ("termine", "Kalender", "event", "Planung"),
    ("assistenz", "KI-Assistent", "auto_awesome", "KI-Assistent"),
    ("mieter", "Mieter", "key", "Anreisen"),
    ("auswertung", "Auswertung", "insights", "Auswertung"),
    ("daten", "Daten einlesen", "upload_file", "Verwaltung"),
    ("inventar", "Inventar", "inventory_2", "Zimmer & Haus"),
    ("einstellungen", "Verwaltung", "settings", "Verwaltung"),
    ("steuerung", "Renovierung & Budget", "query_stats", "Planung"),     # selten genutzt – ganz unten, abgesetzt
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
