# INNternat – Feature-Liste (neue Oberfläche, Version 0.33)

Desktop-Programm zur Belegungs- und Zimmerplanung eines Internats mit mehreren Häusern (Reha-Teilnehmende,
Umschüler/UWT, Mieter). Neue Oberfläche in Python/NiceGUI (eigenes Fenster per pywebview), läuft lokal unter Windows;
Fachlogik und Daten teilt sie mit dem bisherigen PySide6-Programm. Alles läuft offline, die KI ist optional.

## Heute
- Aufgaben als Karten mit 1-Klick-Lösung („dringend“ / „als Nächstes“ / „zur Info“), „Später“ verschiebt auf morgen
- Karten anklickbar: alle betroffenen Fälle; Ausweichzimmer erst prüfen, nur Angehaktes umplanen
- Kennzahlen als Knöpfe (frei, belegt, ohne Zimmer, frei nach Planung, Mängel) mit Sprung zur passenden Stelle
- Frei nach Planung (5 Wochen, gesamt/EMR/Doppelzimmer mit Ampel), neue Personen (7 Tage), Anreisen und Abreisen
- Newsfeed-Ansicht mit Sprach-Briefing; Aufgaben-Center als Panel von rechts

## Anreisen
- Zimmer zuteilen mit grünem Vorschlag, Regeln (Geschlecht, Tier, Gruppe, EMR, Doppelzimmer) und Konfliktprüfung
- Personenangaben, Abreise-Erinnerung (Termin, Kalenderdatei, Outlook), Personen anlegen
- Bestimmtes Zimmer prüfen: warum nicht wählbar (wer/was im Weg ist) und von Hand zuweisen
- Widerspruch Planung ↔ Gebäudeplan sichtbar, Zimmer bis zur Klärung geschützt, per Klick klären
- Gruppen: Hauptmaßnahme, vorbereitende Maßnahme, Assessment, EMR, UWT, Gast, Mieter (Details in der Bemerkung)
- Belegung optimieren (Tauschvorschläge), UWT automatisch zuteilen
- Abreiselisten, Firmenprogramm (was im Belegungssystem einzutragen ist), Anreise- und Schlüssellisten, Zimmerschilder, Excel
- Hinweise aus der Anreiseliste als Marken (Allergiker, Hilfsmittel, Begleitung); Allergiker-Etage (Haus 2, 1. OG) mit
  Vorrang für Allergiker (auch lange Maßnahmen), eigenem Vorschlag, Warnung und Meldung
- „x von y bezugsfertig“ je Anreisetag mit fehlenden Punkten und Vorbereitungsliste

## Zimmer
- Übersicht als Kacheln je Haus/Etage, Stichtag wählbar, mehrere Kacheln kombinierbar, Filter nach Mangelart, Status „nicht bezugsfertig“
- Karten- und Listenansicht mit Filtern (Boden, Renovierung, Merkmale, Personengruppe, Mängel …)
- Zeitstrahl (2/4/8 Wochen); geplante Personen per Drag & Drop in ein anderes Zimmer, mit Regelprüfung
- Flur-Raster: je Flur und Woche die Zahl paralleler Abreisewellen (Ampel), Klick zeigt Wellen und Zimmer
- Zimmerkarte: Bewohner, Zimmer ändern, fest/geplant, Umzug planen, Mängel melden/beheben/unbewohnbar, Notizen mit Wiedervorlage
- Abbruch / vorzeitiger Auszug in der Zimmerkarte – Abreise überall gekürzt, Zimmer wird frei
- Defekte Zimmer nach Dringlichkeit, FM-Bericht (Druck/Excel), Erledigte aus FM-Liste übernehmen
- Drucken und Excel je Auswahl mit „belegt bis / frei ab / frei bis / freie Tage“
- Zimmerhistorie: wer wann im Zimmer war; Suche findet auch ehemalige Bewohner
- Zimmerzustände kontrastreich (frei grün, belegt blau, geplant gestrichelt)

## Reinigung
- Reinigungsliste (heute/Woche) mit Abhaken – einzeln, je Flur oder je Haus –, Wochenblatt zum Aushängen,
  Facility-Checks nach langem Aufenthalt
- Vorschau der Reinigungslast für 6 Wochen je Tag und Haus mit Spitzentagen

## Termine
- Liste (fällig, demnächst, erledigt) und Monatskalender; Klick auf einen Tag legt einen Termin an
- Eigene Termine mit Erinnerung, automatische Termine aus Anreisen, Abreisen und UWT

## Assistenz
- Aufträge in normalen Sätzen (verstehen → prüfen → ausführen, mit Rückgängig)
- Mails einfügen oder aus Outlook holen, Person zuordnen, umsetzen
- Fragen zu den Zahlen; optional KI (Claude oder lokales Modell)

## Mieter
- Mietverträge, Hinweis auf bald endende Verträge, Mail-Entwurf
- Unterlagen als PDF/Word: Mietvertrag, Wohnungsgeberbestätigung, SEPA, Nebenabrede zur Verlängerung
- Flexible Mietverträge als Option (abweichende Textstellen in der Vorlage)
- Vertragsnummern fortlaufend, abgeglichen mit bisherigen Verträgen (Ordner bzw. zuletzt vergebene Nummer); doppelte gesperrt

## Auswertung
- Lage, Belegung (Zeitraum, Personentage, Auslastung, Muster nach Wochentag und Saison)
- Prognose als Executive-Dashboard: 12/24/36 Monate, 80/95-%-Bänder, Backtest
- Szenarien mit Schattenkurve (z. B. ±10 %, Kapazitätskürzung), Kontingente für UWT/Mieter
- Standorte parallel, Netto/Brutto, Präsentationsmodus, Export
- Zimmer & Engpässe (frei jetzt und nach Planung, EMR/Doppel mit Ampel)

## Daten & Import
- Anreiselisten, Einheitslisten und UWT (PDF/Excel), automatisch aus Eingangsordnern beim Start
- Schlüssellisten (An-/Abreisen vom Empfang) abgleichen: Zimmer nach Schlüsselausgabe korrigieren
- Änderungsbericht vor dem Import (geänderte An-/Abreisen, entfallene, neue; betroffene Zimmerplanungen)
- Klassenstärken beim UWT-Import einstellbar
- Gebäudeplan (Word-Datei oder aus der Zwischenablage) mit Abgleich gegen die eigene Planung
- Zimmerkontrollliste (ZKL) mit Abgleich, Zimmer-Pivot
- Belegungs-Pivot (auch vom Server aktualisierbar) mit einstellbarer Pivot-Struktur und Live-Vorschau
- Kapazitäten, Statistik-Importe, manuelle Einträge

## Inventar
- Gegenstände, Ausstattung je Zimmer, Übersicht je Haus, Druck und Excel

## Einstellungen
- Planungsregeln, Erinnerungen, Engpass-Grenzen, KI-Zugang (Schlüssel im Windows-Tresor)
- Zimmer-Stammdaten, Sicherung und Verlauf
- Windows-Meldungen (fällige Termine, Reinigung, Facility-Checks), „Mit Windows starten“
- Tagesbriefing einmal am Tag als Outlook-Termin oder E-Mail an mich – ohne Personennamen

## Übergreifend
- Rückgängig für jede Änderung (Strg+Z), Suche über alles (Strg+K), Panels statt Dialoge
- Alle Listen per Klick auf die Spaltenüberschrift sortierbar (Datum, Zahl, Zimmer natürlich)
- Zähler an den Menüpunkten, Glocke für ungelesene Neuigkeiten
- 4 Layouts (Original, Enterprise Grid, AI-Canvas, Showcase-Dock) × 5 Themes, hell/dunkel, Dichte
- Haptik: Knöpfe geben beim Drücken nach, Arbeitsbalken beim Speichern, einrastende Bestätigung
- Arbeitet parallel zum bisherigen Programm auf denselben Daten; lädt automatisch neu, wenn dort gespeichert wird
