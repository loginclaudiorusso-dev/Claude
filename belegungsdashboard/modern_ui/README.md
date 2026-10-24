# Neue Oberfläche (modern_ui) – Version 0.6.0

Eine neue, ruhige Oberfläche für das ganze Programm. Sie liegt im eigenen Ordner `modern_ui` und **ändert keine
Datei des bisherigen Programms**. Daten und Regeln kommen aus dem Hauptprogramm im Ordner darüber (`belegung`):
dieselben Dateien, dieselben Zuteil-Regeln, dasselbe Rückgängig. Beide Programme zeigen denselben Stand.

## Starten

Das Update-Zip wie immer nach `INNternat` entpacken, dann `INNternat\modern_ui\Start.bat`. Beim ersten Start
(und wenn neue Pakete dazukommen) richtet sie ihre eigene Python-Umgebung ein (`modern_ui\.venv`, einige Minuten).

* Eigenes Fenster (pywebview); klappt das nicht, ein Edge-Fenster ohne Adressleiste. Läuft nur auf dem eigenen
  Rechner (127.0.0.1).
* Bitte nicht gleichzeitig mit dem bisherigen Programm dieselben Dinge ändern. Die neue Oberfläche lädt von selbst
  neu, wenn das Hauptprogramm etwas gespeichert hat (alle 30 Sekunden geprüft).

## Gliederung – eine Ebene, Unteransichten als Umschalter oben

| Seite | Ansichten und Funktionen |
|---|---|
| **Heute** | alles, was zu tun ist (Karten mit 1-Klick-Lösung), **frei nach Planung** (5 Wochen, gesamt/EMR/Doppel mit Ampel), Anreisen der nächsten 7 Tage, Abreisen, Reinigung, Neuigkeiten |
| **Anreisen** | *Zuteilen* (oben „nach Planung mind. … frei“, Zimmer in der Zeile, grüner Vorschlag, Filter, Personenangaben per Klick auf den Namen) · *Abreisen* (heute/morgen/Woche, drucken) · *Firmenprogramm* (was noch einzutragen ist, kopieren, abhaken) · Menü *Mehr*: Anreise-/Schlüsselliste, Zimmerschilder, Person hinzufügen, Planung zurücknehmen, Belegung optimieren, UWT automatisch zuteilen/zurücknehmen |
| **Zimmer** | *Übersicht* (alle Zimmer als Kacheln je Haus und Etage, Tag wählbar, Mängel-Marke, unbewohnbar rot) · *Zeitstrahl* (Haus, 2/4/8 Wochen, Klick öffnet die Zimmerkarte) · *Liste* (Suche, Status, Mängel, Renoviert, Tier …, drucken, FM-Mängelbericht) · *Zimmerkarte*: Bewohner, Zimmer ändern, fest/geplant, Umzug planen/zurücknehmen, Mängel melden/beheben/unbewohnbar, Hinweis, Notizen mit Wiedervorlage, zur Reinigung · *Defekte Zimmer* (nach Dringlichkeit, „behoben“ je Mangel, nächste Anreise, FM-Bericht, FM-Excel, Erledigte aus der FM-Liste übernehmen, für Mail kopieren) |
| **Reinigung** | *Reinigungsliste* (heute/Woche, abhaken, eilige auf einmal, Zimmer hinzufügen, drucken) · *Facility-Checks* |
| **Termine** | *Liste* (fällig, demnächst, erledigt) · *Monat* · eigene Termine anlegen/ändern/löschen |
| **Assistenz** | *Aufträge* in normalen Sätzen (verstehen → prüfen → ausführen, Rückgängig je Auftrag) · *Mails* (einfügen oder aus Outlook, erkennen, Person zuordnen, umsetzen, Posteingang) · *Fragen & Zahlen* (aus den Daten, optional KI) |
| **Mieter** | Verträge, Mail zum Vertragsende (Outlook-Entwurf), *Neuer Mieter* (alle Unterlagen als PDF), *Verlängern* (Nebenabrede Word + PDF), Unterlagen neu erstellen |
| **Auswertung** | *Lage* (heute, Verlauf mit Prognose) · *Belegung* (Zeitraum, Personentage) · *Prognose* (Monate, 80/95 %-Spannen, **Backtest im Diagramm**, Was-wäre-wenn, Modell, Blind-Prognosen) · *Zimmer & Engpässe* (frei jetzt und nach Planung, EMR/Doppel mit Ampel, Lage) · Standort und Netto/Brutto |
| **Daten & Import** | Anreiselisten, UWT, Gebäudeplan (prüfen und übernehmen), ZKL mit Abgleich, Zimmer-Pivot, Belegungs-Pivot (auch vom Server), Kapazitäten, Mieten/Anreisen für die Statistik, manuelle Einträge |
| **Inventar** | *Gegenstände* (Bestand, verteilt, im Lager, verteilen/entfernen) · *Zimmer* (Ausstattung ändern, kopieren) · Inventarliste drucken |
| **Einstellungen** | *Allgemein* (Zimmerplanung, Erinnerungen, Engpass-Grenzen, KI) · *Zimmer-Stammdaten* · *Sicherung & Verlauf* |

**Kennzahlen sind Knöpfe** (neu in 0.5): Ein Klick filtert (z. B. Zimmer-Übersicht „frei“, Reinigung „erledigt“,
defekte Zimmer „dringend“, Anreise „ohne Zimmer“, Mieter „Mail offen“) oder springt an die passende Stelle (auf
Heute: „frei“ → Zimmer-Übersicht, „ohne Zimmer“ → Zuteilen, „nach Planung“ → Engpässe, „Mängel“ → defekte Zimmer).
Nochmal klicken hebt den Filter auf. Knöpfe und Umschalter sind plastischer gestaltet.

Überall: **Strg+K** sucht Personen, Zimmer und Seiten · **Strg+Z** bzw. „Rückgängig“ nimmt die letzte Änderung
zurück · Aufgaben und Formulare gleiten als **Panel von rechts** herein, der Hintergrund wird abgedunkelt –
Klick daneben oder Esc schließt · **A** öffnet die Aufgaben.

**Neu in 0.6 – moderner und verständlicher für neue Nutzer:**
* Aufgaben-Karten mit Symbol je Aufgabentyp (Anreise, Reinigung, Mängel, Termin, Mail …), mehr Luft;
  **dringend** = roter linker Rand mit leichtem Leuchten, *als Nächstes* = orange, *zur Info* = violett.
* Hauptknöpfe mit violett-indigo Verlauf, alle Knöpfe reagieren auf Maus (leicht größer, heller, Klick-Feedback).
* Glas-Optik (halbtransparente, weichgezeichnete Flächen) für Navigation, Kopf, Blöcke und Panel; rundere Ecken.
* Kennzahlen in Monospace-Ziffern mit Symbol; **Zustände überall gleich**: frei grün ✓, belegt blau, geplant violett,
  gesperrt grau, Mängel orange „!“, unbewohnbar rot (Legende, Zimmerliste, defekte Zimmer, Zimmerkarte).
* „Willkommen“-Kasten auf *Heute* mit fünf ersten Schritten – verschwindet dauerhaft mit „Verstanden“.

### Gegenüber dem bisherigen Programm

* PDFs (Mietunterlagen, Nebenabrede) erstellt hier Microsoft Edge im Hintergrund; ohne Edge wird der Mietvertrag als
  HTML gespeichert und zum Drucken geöffnet. Ablage: zuletzt genutzter Export-Ordner bzw. `Mietunterlagen` im Datenordner.
* Drucken öffnet eine Druckansicht im Browser (drucken oder als PDF speichern).
* Statistik-Listen (Mieten/Anreisen) werden mit automatischer Spaltenzuordnung gelesen; passt sie nicht, bitte
  einmal im Hauptprogramm mit Spaltenwahl importieren – danach merkt sich das Programm die Zuordnung.
* Darstellung (Designs, hell/dunkel) gibt es hier nicht – die neue Oberfläche ist bewusst ein ruhiges dunkles Design.

## Aufbau

| Datei | Inhalt |
|---|---|
| `app.py` | Start (Fenster bzw. Edge), Protokoll `modern_ui.log` |
| `modern/oberflaeche.py` | Rahmen (Seitenleiste, Kopf, Panel rechts, Hinweis mit Rückgängig, Tasten) und Zuteilen |
| `modern/register.py` | Gliederung: Seiten, Reihenfolge, Gruppen |
| `modern/seite_*.py`, `modern/seiten.py` | die Seiten |
| `modern/*_kern.py`, `modern/kern.py` | Daten und Änderungen über das Hauptprogramm, ohne Oberfläche – testbar |
| `modern/stil.py` | Farben und Stil, alle Farbwerte nur hier |
| `tests/` | Tests mit erfundenen Namen: `python -m pytest modern_ui/tests` |

## Rückgängig machen / entfernen

Den Ordner `modern_ui` löschen genügt – das bisherige Programm und seine Daten bleiben. Sicherungen: vor 0.1.0
`backup/v6.28.0`, vor 0.2.0 `backup/modern-0.1.0`, vor 0.3.0 `backup/modern-0.2.0`, vor 0.4.0 `backup/modern-0.3.0`, vor 0.5.0 `backup/modern-0.4.0`, vor 0.6.0 `backup/modern-0.5.0` (jeweils auch als Zip in `Sicherung`).
