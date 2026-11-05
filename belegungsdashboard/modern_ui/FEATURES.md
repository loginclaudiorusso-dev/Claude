# INNternat – Feature-Liste (neue Oberfläche, Version 0.61.0)

Desktop-Programm zur Belegungs- und Zimmerplanung eines Internats mit mehreren Häusern (Reha-Teilnehmende,
Umschüler/UWT, Mieter). Neue Oberfläche in Python/NiceGUI (eigenes Fenster per pywebview), läuft lokal unter Windows;
Fachlogik und Daten teilt sie mit dem bisherigen PySide6-Programm. Alles läuft offline, die KI ist optional.

## Heute
- Tageszentrale (Standard): Kennzahlen, „Als Nächstes“ nummeriert mit direkter Aktion, nächste 7 Tage (bezugsfertig), freie Zimmer 5 Wochen mit EMR/DZ, Outlook-Vorschau (nur lesen)
- Postfach wie Outlook: links Aufgaben, rechts alle Fälle mit Einzel- und Sammelaktion; Erledigtes verschwindet, Pfeiltasten; Umschalter zur bisherigen Übersicht
- Schloss/Schlüssel defekt: FM-Auftrag mit Frist (nächster Einzug) statt Umplanen, solange die Anreise ≥ 3 Tage entfernt ist
- Aufgaben als Karten mit 1-Klick-Lösung („dringend“ / „als Nächstes“ / „zur Info“), „Später“ verschiebt auf morgen
- Karten anklickbar: alle betroffenen Fälle; Ausweichzimmer erst prüfen, nur Angehaktes umplanen
- Kennzahlen als Knöpfe (frei, belegt, ohne Zimmer, frei nach Planung, Mängel) mit Sprung zur passenden Stelle
- Frei nach Planung (5 Wochen, gesamt/EMR/Doppelzimmer mit Ampel), neue Personen (7 Tage), Anreisen und Abreisen
- Newsfeed-Ansicht mit Sprach-Briefing; Aufgaben-Center als Panel von rechts

## Anreisen
- Zimmer zuteilen mit grünem Vorschlag, Regeln (Geschlecht, Tier, Gruppe, EMR, Doppelzimmer) und Konfliktprüfung
- Personenangaben, Abreise-Erinnerung (Termin, Kalenderdatei, Outlook), Personen anlegen
- Bestimmtes Zimmer prüfen: warum nicht wählbar (wer/was im Weg ist) und von Hand zuweisen
- Mietvertrag nachträglich bearbeiten (Zimmer, Zeitraum, Name, Miete, Vertragsnummer …), Zimmerplan und Verlauf ziehen mit
- Vertragsnummer immer mit dem Jahr des Vertrags bzw. des Mietbeginns; Zimmer mit Bestätigung „trotzdem nehmen“
- Sperre laut Gebäudeplan früher beenden („fertig renoviert ab …“) mit Bestätigung, zurücknehmbar
- Mieter sind von der Männer-Regel (Haus 6, Bad über den Flur) ausgenommen
- Widerspruch Planung ↔ Gebäudeplan sichtbar, Zimmer bis zur Klärung geschützt, per Klick klären
- Gruppen: Hauptmaßnahme, vorbereitende Maßnahme, Assessment, EMR, UWT, Gast, Mieter (Details in der Bemerkung)
- Belegung optimieren (Tauschvorschläge), UWT automatisch zuteilen
- Abreiselisten, Firmenprogramm (was im Belegungssystem einzutragen ist), Anreise- und Schlüssellisten, Zimmerschilder, Excel
- Hinweise aus der Anreiseliste als Marken (Allergiker, Hilfsmittel, Begleitung); Allergiker-Etage (Haus 2, 1. OG) mit
  Vorrang für Allergiker (auch lange Maßnahmen), eigenem Vorschlag, Warnung und Meldung
- „x von y bezugsfertig“ je Anreisetag mit fehlenden Punkten und Vorbereitungsliste

- Archiv früherer Anreisen (Mehr → Archiv): beliebiger Zeitraum, Suche nach Name/Maßnahme/Gruppe/Zimmer, Zimmer laut Planung, Gebäudeplan oder Zimmerhistorie; Drucken und Excel

## Zimmer
- Zimmer hinzufügen, die im Gebäudeplan fehlen (Einstellungen → Zimmer-Stammdaten oder Zimmer → Bearbeiten); entfernen: selbst angelegte löschen, Zimmer aus dem Gebäudeplan auf „gehört nicht zum Internat“
- Änderungen je Zeitraum (Zuteilungen, Umzüge/Auszüge, Mängel) mit Excel-Export
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
- Prognose: Kennzahlen und PDF über den gewählten Zeitraum, „Monate an der Warnschwelle“ (Schwellenprüfung), ab Monat 13 als fortgeschrieben markiert, Erklärungen sichtbar
- Lage, Belegung (Zeitraum, Personentage, Auslastung, Muster nach Wochentag und Saison)
- Prognose als Executive-Dashboard: 12/24/36 Monate, 80/95-%-Bänder, Backtest
- Szenarien mit Schattenkurve (z. B. ±10 %, Kapazitätskürzung), Kontingente für UWT/Mieter
- Standorte parallel, Netto/Brutto, Präsentationsmodus, Export
- Zimmer & Engpässe (frei jetzt und nach Planung, EMR/Doppel mit Ampel); Klick zeigt je Woche freie Zimmer je Tag, welche Zimmer frei/belegt und von wem

## Daten & Import
- Bad Pyrmont/Weser-Ems: Anreiselisten als PDF „Teilnehmer Beginn“ (K = Internat, Abreise = Maßnahmeende, ohne Geburtsdatum)
- Anreiselisten, Einheitslisten und UWT (PDF/Excel), automatisch aus Eingangsordnern beim Start – danach Bericht, was sich geändert hat (mit Rückgängig)
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
- Haus 6: Aufteilung je Etage (schaltbar, mit Vorschau): Hauptmaßnahmen in Zimmern mit eigenem Bad, Vorrang Mieter x01/x02 und UWT x08/x09 auf renovierten Etagen; Bad über den Flur = x01, x02, x08, x09 (nur Männer)
- Planungsregeln, Erinnerungen, Engpass-Grenzen, KI-Zugang (Schlüssel im Windows-Tresor)
- Zimmer-Stammdaten, Sicherung und Verlauf
- Windows-Meldungen (fällige Termine, Reinigung, Facility-Checks), „Mit Windows starten“
- Tagesbriefing einmal am Tag als Outlook-Termin oder E-Mail an mich – ohne Personennamen

## Maßnahmen-Prognose (Auswertung → Maßnahmen)
- Maßnahmen im Vergleich: Teilnehmende je Maßnahmenart (alle, nicht nur Internat), jede als eigene Kurve – Ist durchgezogen, Prognose gestrichelt (gebuchter Bestand + erwartete neue Kurse aus bis zu drei Vorjahren); keine Summe, keine Betten (die stehen in der allgemeinen Prognose)
- Auswahl einer oder mehrerer Maßnahmen (mit Suche, leer = alle, „Nur Hauptmaßnahmen“); Darstellung „Ein Diagramm“ oder „Je Maßnahme“ (Raster kleiner Diagramme, gleiche oder eigene Skala; ab 6 Maßnahmen Standard); 12/24/36 Monate
- Kennzahlen: am stärksten gewachsen/geschrumpft, höchster/niedrigster Verbleib
- Vergleichstabelle: Teilnehmertage 12 Monate, Trend zum Vorjahr, Starts je Jahr, Kursgröße jetzt/früher, Verbleib, heute/in 12/in 24 Monaten; Gruppe je Art änderbar
- Geplante Plätze je Art und Startmonat, erwartete neue Kurse, Rückwärtstest
- Import: Maßnahmen-Pivot (nur Zählwerte je Kurs und Tag, keine Namen; fehlende Tage werden überbrückt; Bestätigung mit Zusammenfassung) und Anreiselisten „Teilnehmer Beginn“ als Word oder PDF (P = Pendler, ohne P Internat, K = Kostenzusage)

## Steuerung (Leitung, ganz unten in der Seitenleiste)
- Bereiche nach Fragen: Cockpit · Vorhaben · Zeitplan & Kapazität · Finanzen · Grundlagen; rechnet erst beim Öffnen; gilt für Goslar
- Cockpit (nur lesen): 5 Kennzahlen (Bau verplant, Bau frei – verfällt am 31.12., Möbelantrag, offene A-Zimmer, Warnmonate), 3 Warnungen, 3 Handlungsempfehlungen; jede Kachel führt zur passenden Ansicht
- Vorhaben (Grundmodell Vorhaben → Maßnahmen → Kostenpositionen): Portfolio-Liste aller Arten (Renovierung, Möbel, Technik, Brandschutz, Außenanlage, IT, Sonstiges) mit Filter; genau ein Haupttreiber (Pflicht nur mit Nachweis); drei Statusachsen: Entscheidung von Hand (Datum, Wer), Umsetzung aus Terminen/Auftrag, Finanzen aus Auftrag/Rechnungen; Widersprüche als Hinweis
- Kostenposition: Betrag, Herkunft, Haushaltsjahr, Topf (Bau/Möbel/sonstiges), gültig bis, Auftrag, Rechnungen mit „bezahlt am“
- „Renovierung <Jahr>“ erscheint automatisch als Vorhaben aus den Vormerkungen (eine Quelle); Entscheidung, Aufträge und Rechnungen dazu werden ergänzt
- Andere Vorhaben verbrauchen ihren Topf: Baubudget, Cockpit und Finanzen rechnen sie mit, der Renovierungsvorschlag verteilt den Rest
- Werkzeug „Renovierung planen“ in drei Zonen Eingabe | Ergebnis | Entscheidung
- Zeitplan & Kapazität: Gantt der Renovierung, Termine weiterer Vorhaben, Belegung Ist/Prognose/Vorjahr/Kapazität minus Baustellen, Prognosegüte, Kernbestand
- Finanzen: Budget je Topf (Bau, Möbel/Einrichtung, sonstiges) und Haushaltsjahr (= Kalenderjahr), Planjahr und Folgejahr: Budget, verbraucht (Regel je Topf, Standard beim Auftrag), geplant offen, Vorschlag, frei, gebunden/abgerechnet/bezahlt; Klick zeigt die Positionen; Budget je Jahr & Regeln einstellbar; Freigabe in einer Stufe (Leitung); Strategie 5 Jahre mit Planungshorizont (belastbar / wahrscheinlich / Orientierung)
- Grundlagen: Annahmen mit Herkunft, Angebote mit Datum und Gültigkeit, Kennzahlen und Datenlücken
- Nie nur zum Ausschöpfen: bei gleichem Bedarf die günstigere Lösung, Etagen ohne Bedarf zählen nicht; Restbudget bleibt sichtbar frei
- Festpreis: solange ein Angebot gilt („gültig bis“, wird im PDF erkannt; ohne Angabe bis 31.12. des Angebotsjahres), keine Preissteigerung
- Renovierung: Baubudget als feste Grenze (Standard) oder Zimmerziel; Möbelbedarf als Antrag; Haus-Vorrang; Kernbestand-Häkchen
- Ganze Etage selbst planen: Etage wählen, Kosten und besten Monat sehen, vormerken – Vormerkungen verbrauchen Budget/Ziel, der Vorschlag verteilt den Rest
- Bedarf in Klassen A/B/C, getrennt für Bau und Möbel; frisch renoviert = kein Bau
- Maßnahmen: ganze Etage, Einzelzimmer komplett, nur Möbel; beste Kombination (Etagen + Einzelzimmer nach Bedarf je €), Robustheitssatz
- Kosten mit Herkunft (Angebot/Eingabe/Schätzung/Platzhalter), Bau „laut Angebot“ separat, Puffer je Budget (Standard 0 %), Spanne, T€-Rundung, Hinweis bei Platzhaltern
- Angebot-PDF einlesen (auch mit breiten Abständen im PDF-Text; Möbel für alle Häuser): Summe, Haus, Möbel-Zimmerzahl, Einheitspreise (Boden/Wand/Tür) aus den Positionen; Einzelzimmer = Einheitspreise × Fläche
- Zeitplan als Gantt: Belegungsstopp, Bauzeit, Vorschläge gestrichelt, ⚑ Ausweich fehlt, ▲ Warnschwelle, grau = nicht prüfbar; Einzelzimmer in Kampagnen nach Möbel-Lieferzeit; Übernehmen mit Bestätigung
- Kernbestand und Reserve mit Vorschlag ganzer Reserve-Etagen und Fehlbetten bei +10 % Nachfrage
- Strategie 5 Jahre mit Alterung: Nichtstun, Empfohlen, −20 %, +50 %, Kernbestand
- Entscheidungsvorlage (PDF): 1 Seite Kurzfassung mit Beschlussfeld (Bau/Möbel) + Anhang A–H mit Erläuterungen
- Kennzahlen: verfügbare Betten, Auslastung, Belegtage je Gruppe, Ausfalltage, offene A-Zimmer, Zyklus, Kernbestand, Reserve; Werte eingeben (Tagessätze, Abweisungen, Zustandsnoten)

## Übergreifend
- Laptop-tauglich: unter 1200 px schmale Seitenleiste automatisch, Tabellen scrollen waagerecht, kompaktere Tageszentrale
- Darstellung „INNternat“: Türkis-Grau, hell/dunkel umschaltbar in der Seitenleiste, Bahnschrift/Candara, Kontraste ≥ 4,5:1, Logo aus Datei
- Drei Standorte (Goslar, Bad Pyrmont, Weser-Ems): Auswahl beim Start, Wechsel über das Logo; Verwaltung je Standort getrennt (eigener Datenordner), Auswertung und Prognose über alle
- Rückgängig für jede Änderung (Strg+Z), Suche über alles (Strg+K), Panels statt Dialoge
- Panels mit Eingaben fragen vor dem Schließen („Eingaben verwerfen?“) – nichts geht durch Esc oder Fehlklick verloren
- „Stand 14:32“ in der Kopfzeile: wann die Daten zuletzt geladen wurden, leuchtet bei Änderungen aus dem Hauptprogramm
- Alle Listen per Klick auf die Spaltenüberschrift sortierbar (Datum, Zahl, Zimmer natürlich), auch per Tastatur (Tab, Enter)
- Kleinschrift mit Kontrast ≥ 4,5:1 (WCAG)
- Zähler an den Menüpunkten, Glocke für ungelesene Neuigkeiten
- Showcase-Dock: Standort, angeheftete Bereiche (anpassbar), je Gruppe ein Menü, Suche, hell/dunkel; anheften oder automatisch ausblenden (fährt beim Darüberfahren herein, Strg+B)
- Seitenleiste wie in Office: einklappen, beim Darüberfahren klappt sie über dem Inhalt auf, „Leiste anheften“ hält sie offen (Strg+B)
- Tabellenvorlage: Kopfzeile und Zeilen teilen ein Spaltenraster – nichts verrutscht
- Auslastung in der Zimmerliste ohne Gästezimmer (die Gästeetage läuft unabhängig vom Tagesgeschäft)
- Standard „Original“; unter „Weitere Darstellungen“: 4 Layouts (Original, Enterprise Grid, AI-Canvas, Showcase-Dock) × 6 Themes (INNternat, Original, inn-tegrativ, Linear Monochrome, Executive Obsidian, Soft Nordic), hell/dunkel, Dichte
- Haptik: Knöpfe geben beim Drücken nach, Arbeitsbalken beim Speichern, einrastende Bestätigung
- Arbeitet parallel zum bisherigen Programm auf denselben Daten; lädt automatisch neu, wenn dort gespeichert wird

## Netzwerkordner (mehrere PCs)
- Ein Paket zum Entpacken: `INNternat starten.bat`, `Programm\`, `Daten\` – Updates ersetzen nur `Programm`
- Jeder PC startet selbst; Python-Umgebung, Protokoll und persönliche Einstellungen lokal je PC, Desktop-Verknüpfung
- Daten aus dem bisherigen Ordner übernehmen (prüfen, kopieren, alter Ordner bleibt unverändert)
- Schreibsperre über alle PCs, Speichern und Lesen mit Wiederholung bei gesperrten Dateien
- „Aktualisiert: … – gespeichert von …“ auf den anderen PCs; Hinweis bei neuer Version
- Tägliche automatische Sicherung aller Standorte durch genau einen PC
- Schreibsperre mit Herzschlag (verwaist nach 45 s, lange Schritte bleiben gültig)

## Maßnahmen: Neuanmeldungen (0.56)
- Neuanmeldungen je Startwelle (Winter Nov–Apr, Sommer Mai–Okt), alle Teilnehmenden, als Grundlage für den Wirtschaftsplan
- Verfahren automatisch per Rückwärtstest gewählt (wie Vorjahr, Mittel 3 Jahre, gewichtetes Mittel, gedämpfter Trend)
- Gebuchte Starts + Nachbuchung, 80-%- und 95-%-Spanne aus dem Rückwärtstest (Band im Diagramm, Umschalter in der Tabelle), eigene geplante Plätze
- Eingestellte und Kleinstmaßnahmen sowie UWT ausgeblendet, von Hand ein- und ausblendbar
- Werte beim Darüberfahren (Ist, erwartet, 80-/95-%-Band), Rückwärtstest je Welle im Diagramm mit Trefferquote der Bänder
- Live-Suche (Zimmer, Personen, Inventar); Ein-Tasten-Kürzel im Postfach (L, S) und im Abtipp-Modus (1–6, E, N, ←/→)

## Maßnahmen-Prognose (Rechenweg 0.55)
- Gebuchte Kurse × Verbleibskurve früherer Kurse derselben Art (bedingt auf die bisherige Dauer)
- Teilweise gebuchte Kurse plus erwartete Nachbuchung (Poisson-Gamma, Buchungskurve aus den Anreiselisten gemessen)
- Kurzkurse als Saisonsockel je Monat; Rückwärtstest nur mit dem Wissen am Stichtag, mit Vergleich ohne Verbleib
- Abtipp-Modus fürs Firmenprogramm: Feld für Feld kopieren, schmaler Streifen im Vordergrund
