"""Belegungsdashboard – fachlicher Kern (ohne Qt), damit er testbar bleibt.

Aufbau:
    konfig      Konstanten, Standorte, Programmordner
    speicher    JSON-Ablage (atomar) für Einstellungen und lokale Daten
    pivot       Pivot-Profil + Einlesen (openpyxl ohne Excel, oder Excel-COM mit Refresh)
    importe     Excel-Listen (Mieten, Anreisen) mit Spaltenerkennung
    datenstand  Datenmodell + Aggregation (Belegung je Tag, Aufschlüsselung, Kapazität)
    prognose    Monatsprognose mit Backtest-Modellauswahl und horizontabhängigen Bändern
    laden       Orchestrierung: Quelle -> Datenstand
    assistent   Chat-Assistent (präzise Datenantworten + optional LLM mit Werkzeugen)
"""

__version__ = "5.14.0"
