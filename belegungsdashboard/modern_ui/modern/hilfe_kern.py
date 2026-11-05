"""Hilfe (0.68): kurze Erklärung je Seite und Ansicht, erste Schritte, Tastenkürzel. Rein, ohne NiceGUI.
Geöffnet mit F1, dem „?“ in der Titelleiste oder Datei → Hilfe – immer passend zur gerade offenen Seite."""

from __future__ import annotations

# Seite → (Titel, Kurzbeschreibung, [Punkte]); optional je Ansicht eigene Punkte in ANSICHT
SEITEN = {
    "heute": ("Heute", "Der Tag auf einen Blick: was dringend ist, wer anreist, was gereinigt werden muss.", [
        "Die Kacheln oben sind Knöpfe – ein Klick springt zur passenden Stelle (z. B. Anreisen ohne Zimmer).",
        "„Offene Aufgaben“ sind nach Dringlichkeit sortiert. Der farbige Knopf löst eine Aufgabe mit einem Klick, "
        "„Später“ blendet sie bis morgen aus.",
        "„Aufgaben“ öffnet das Postfach: links alle Aufgaben, rechts die einzelnen Fälle mit Einzel- und Sammelaktion.",
    ]),
    "anreisen": ("Anreisen", "Personen der Anreiselisten ein Zimmer geben – nach denselben Regeln wie im Hauptprogramm.", [
        "Oben die Anreise wählen; je Person das Zimmer in der Zeile wählen. Grün ist der passende Vorschlag.",
        "„Alle Vorschläge übernehmen“ (in der Aufgabe unter Heute) teilt alle grünen Vorschläge auf einmal zu. "
        "Gespeichert wird sofort.",
        "Im Menü ⋯ der Seite: Anreiseliste, Schlüsselliste und Zimmerschilder drucken.",
    ]),
    "zimmer": ("Zimmer", "Alle Zimmer mit Belegung, Sperren und Mängeln.", [
        "Ein Zimmer anklicken öffnet die Zimmerkarte: Bewohner, Verlauf, Mängel, Sperre.",
        "Eine Sperre (z. B. Renovierung) lässt sich in der Zimmerkarte früher beenden („fertig renoviert ab …“).",
        "Filter oben (Tag, Haus, frei/belegt/gesperrt) wirken sofort.",
    ]),
    "reinigung": ("Reinigung", "Was vor dem nächsten Einzug gereinigt werden muss.", [
        "Erledigtes abhaken – die Liste ist auf allen PCs gleich.",
        "„Vorschau 6 Wochen“ zeigt die Last je Woche, „Facility-Checks“ die wiederkehrenden Prüfungen.",
    ]),
    "termine": ("Termine", "Termine und Wiedervorlagen – mit Erinnerung als Windows-Meldung.", [
        "Neue Termine über „Neuer Termin“; fällige erscheinen auch unter Heute.",
    ]),
    "assistenz": ("Assistenz", "Aufträge, Mails und Fragen an die Daten.", [
        "„Fragen & Zahlen“ beantwortet Fragen wie „Wie viele Plätze sind im November frei?“.",
    ]),
    "mieter": ("Mieter", "Mieter und Mietverträge.", [
        "Vertragsnummern laufen je Jahr (z. B. 27-001); die Nummer lässt sich beim Bearbeiten ändern.",
        "Für Mieter gilt die Trennung nach Geschlecht bei den Zimmern in Haus 6 nicht.",
    ]),
    "auswertung": ("Auswertung", "Lage, Belegung und Prognosen – für alle Standorte.", [
        "Die Prognose zeigt den erwarteten Verlauf mit 80-%- und 95-%-Spanne; der Rückwärtstest zeigt, wie gut sie früher "
        "getroffen hätte.",
        "Diagrammtyp, Legende und Elemente stehen in der Registerkarte „Diagramm“.",
    ]),
    "steuerung": ("Steuerung", "Renovierung, Zeitplan, Kapazität und Finanzen – für die Leitung.", [
        "Vorhaben anlegen, im Zeitplan einplanen und die Wirkung auf freie Zimmer prüfen.",
    ]),
    "daten": ("Daten & Import", "Listen einlesen und den Datenstand prüfen.", [
        "Anreiselisten, Gebäudeplan und Pivot hier einlesen; das Programm zeigt, was neu ist.",
    ]),
    "inventar": ("Inventar", "Gegenstände je Zimmer und Haus.", ["Im Menü ⋯ der Seite: Inventarliste drucken."]),
    "einstellungen": ("Einstellungen", "Programm, Zimmer-Stammdaten, Sicherung.", [
        "Die Darstellung (Farben, Zoom, Schrift) steht unter Datei → Optionen.",
    ]),
}
ANSICHT = {
    ("anreisen", "personen"): ["Alle Personen der Anreiselisten; „neu“ zeigt, wer in den letzten 7 Tagen dazukam."],
    ("anreisen", "abreisen"): ["Abreisen im gewählten Zeitraum – mit Druck der Abreiseliste."],
    ("anreisen", "eintragen"): ["Buchungen, die im Programm geplant, aber noch nicht im Belegungssystem stehen. "
                                "„Kopieren“ legt die Zeilen in die Zwischenablage; danach abhaken. Der Abtipp-Modus "
                                "zeigt Eintrag für Eintrag (Tasten 1–6 kopieren ein Feld, E erledigt, N nächster)."],
    ("zimmer", "zeitstrahl"): ["Belegung über mehrere Wochen; gesperrt ist grau, Konflikte sind rot umrandet."],
    ("zimmer", "maengel"): ["Zimmer mit offenen Mängeln – FM-Auftrag per Mail oder Mängelbericht drucken."],
    ("zimmer", "aenderungen"): ["Was im Zeitraum geändert wurde – Zuteilungen, Umzüge, Auszüge, Mängel – auch als Excel."],
    ("auswertung", "massnahmen"): ["Neuanmeldungen je Startwelle (Winter/Sommer) und Maßnahme, mit Prognose und Spanne."],
    ("auswertung", "prognose"): ["Taste P startet die Präsentation (← → Schritt für Schritt, Esc beendet)."],
}
ERSTE_SCHRITTE = [
    ("Registerkarten", "Oben wie in Word und Excel: Start (Heute, Termine, Assistenz), Anreisen, Zimmer & Haus, "
                       "Auswertung, Verwalten. Ein Klick auf eine Schaltfläche öffnet die Ansicht; ein Punkt am Reiter "
                       "zeigt, wo die offene Seite liegt."),
    ("Suchen", "Das Suchfeld oben (Strg+K) findet Personen, Zimmer und Seiten."),
    ("Rückgängig", "Jede Änderung lässt sich mit Strg+Z oder dem Pfeil oben links zurücknehmen."),
    ("Automatisch gespeichert", "Es gibt kein „Speichern“: jede Änderung ist sofort gespeichert – auch für die "
                                "anderen PCs."),
    ("Neuigkeiten", "Die Glocke oben rechts zeigt neue Meldungen; die Zahl verschwindet, wenn sie gelesen sind."),
    ("Darstellung", "Zoom, Kompakt, Vollbild und Hell/Dunkel unten rechts in der Statusleiste; Farben, Schrift und "
                    "Programm-Einstellungen unter Datei → Optionen."),
    ("Standort", "Der Standort steht oben neben „INNternat“ – Klick wechselt ihn."),
]
TASTEN = [
    ("Strg+K", "Suchen"), ("Strg+Z", "Letzte Änderung zurücknehmen"), ("Strg+P", "Aktuelle Ansicht drucken"),
    ("F1", "Hilfe zur aktuellen Seite"), ("A", "Aufgaben-Center ein/aus"), ("Esc", "Panel oder Dialog schließen"),
    ("↑ ↓", "Aufgabe im Postfach wählen"), ("L · S", "Aufgabe lösen · auf später legen (Postfach)"),
    ("1–6 · E · N", "Abtipp-Modus: Feld kopieren · erledigt · nächster"), ("P", "Präsentation der Prognose"),
    ("Strg+Umschalt+L", "Zur Leitstand-Workbench und zurück"),
]


def fuer(seite: str, ansicht: str | None) -> tuple[str, str, list[str]]:
    titel, text, punkte = SEITEN.get(seite, ("Hilfe", "", []))
    return titel, text, ANSICHT.get((seite, ansicht or ""), []) + punkte


# Druckausgaben je Seite/Ansicht: (Text, Schlüssel) – die Oberfläche ruft die vorhandenen Druckfunktionen auf
DRUCK = {
    ("anreisen", "zuteilen"): [("Anreiseliste", "anreise"), ("Schlüsselliste", "schluessel"),
                               ("Zimmerschilder", "schilder")],
    ("anreisen", "abreisen"): [("Abreiseliste", "abreise")],
    ("reinigung", "liste"): [("Reinigungsliste", "reinigung"), ("Wochenblatt zum Aushängen", "wochenblatt")],
    ("zimmer", "uebersicht"): [("Zimmerliste mit Bewohnern", "zimmer_liste"), ("Zimmerliste ohne Namen", "zimmer_ohne"),
                               ("FM-Mängelbericht", "fm")],
    ("zimmer", "maengel"): [("FM-Mängelbericht", "fm")],
}


def druckausgaben(seite: str, ansicht: str | None) -> list[tuple[str, str]]:
    return DRUCK.get((seite, ansicht or ""), [])
