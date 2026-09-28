# Belegungsdashboard 4.0

Desktop-Dashboard für die Internatsbelegung der INN-tegrativ gGmbH (Bad Pyrmont, Goslar,
Weser-Ems): Lage heute, Verlauf, Prognose mit ehrlicher Unsicherheit, Listen-Import und ein
Chat-Assistent, der jede Zahl direkt aus den Daten berechnet.

## Start

```bash
pip install -r requirements.txt
python belegungsdashboard_gui.py              # öffnet zuletzt genutzte Datei bzw. pivot_neu.xlsx
python belegungsdashboard_gui.py pfad\zur\pivot.xlsx
python belegungsdashboard_export.py            # schreibt den Datenblock in Belegungsdashboard.html
python -m pytest tests                         # 42 Tests für Pivot, Prognose, Import, Assistent, Export
pyinstaller belegungsdashboard_gui.spec        # dist/Belegungsdashboard.exe + dist/Belegungsdashboard-Export.exe
```

Einstellungen und lokale Listen liegen wie bisher neben der exe
(`kapazitaeten_manuell.json`, `manuelle_eintraege.json`, `pivot_profile.json` werden
weiterverwendet; neu: `einstellungen.json`, Ordner `importe/`). Mit der Umgebungsvariable
`BELEGUNG_DATEN` lässt sich der Ordner umlenken, z. B. auf ein Netzlaufwerk.

## Was sich gegenüber 3.x geändert hat

### Daten

* **Pivot ohne Excel lesen.** „Aktualisieren“ liest die in der .xlsx gespeicherten
  Pivot-Werte direkt (openpyxl) – in ca. 1 Sekunde, ohne Excel-Start, auch wenn die Datei
  gerade in Excel offen ist. Der OLAP-Abruf vom Server (Excel im Hintergrund, Netz/VPN nötig)
  ist ein eigener Menüpunkt „Pivot vom Server abrufen“.
* **Zukunftswerte der Pivot sind gebuchter Bestand, keine Platzhalter.** Die Werte nach dem
  Abrufdatum fallen stufenweise und steigen nie – das Muster von Teilnehmenden mit geplantem
  Maßnahmeende, ohne künftige Neuaufnahmen. Die Vorversion hat sie verworfen; jetzt sind sie
  die Untergrenze der Prognose und werden als „gesichert“ angezeigt.
* **Stichtag = Abrufdatum der Pivot** (aus dem Pivot-Cache), nicht einfach „heute“. War die
  Datei drei Tage nicht aktualisiert, wird das angezeigt, statt Bestand als Ist auszugeben.

### Import von Mieten und Anreisen (neu)

Unter **Daten & Import** eine Excel- oder CSV-Liste hochladen. Kopfzeile (auch unter
Titelzeilen) und Spalten werden automatisch erkannt (z. B. „Mietbeginn“, „Anreise“,
„Einrichtung“, „Anzahl Betten“, „Mieter / Firma“); Standorte werden normalisiert
(„BP“, „Bad Pyrmont“, „BFW BP“ …). Vor dem Import zeigt eine Vorschau, was übernommen wird
und welche Zeilen warum übersprungen werden. Die Zuordnung wird je Dateiname gemerkt, ein
erneuter Upload ersetzt den alten Stand.

* **Mieten** zählen zur Netto-Belegung (ohne Ende = unbefristet; leerer Standort = Goslar wie bisher).
* **Anreisen** ergänzen Belegung und Prognose **ab dem Tag nach dem Stichtag** – vergangene
  Tage stehen bereits in der Pivot, sonst würde doppelt gezählt. Ohne Abreise-Spalte zählen
  sie nur als Termin oder mit einer wählbaren Standard-Aufenthaltsdauer.

### Statistik

| Vorher | Jetzt |
|---|---|
| Modellwahl per In-Sample-AIC; Holt-Winters mit 3 statt ~17 Parametern gezählt → komplexes Modell systematisch bevorzugt | Rollierender **Backtest** über 18 Monate: jedes Modell wird nur mit damals verfügbaren Daten gerechnet, gewählt wird der kleinste mittlere Fehler |
| Band überall gleich breit (feste RMSE) | Band wächst mit dem Horizont (√h) und ist **kalibriert**: im Backtest liegen 80 % der Fälle im 80 %-Band |
| Goslar-Nullwerte vor der Eröffnung 2021 als Historie | Strukturbruch wird erkannt und abgeschnitten |
| Laufender Monat (Teilmonat) als Trainingspunkt | Laufender Monat = Ist-Tage + Prognose der Resttage |
| Untergrenze = Mieter + Gäste (andere Einheit als die Reha-Prognose) | Untergrenze = gebuchter Bestand + importierte Anreisen |
| Gesamt-Band: Standorte als unabhängig angenommen | Gesamt-Band aus den Backtest-Fehlern der Summe |
| Platzhalter „Sicherheit 0,7“ | entfernt; stattdessen gemessene Trefferquote |
| „Rückblick“ = Anpassung an bekannte Werte | echte Blind-Prognosen (1 Monat voraus) |

Kandidaten: Holt-Winters mit gedämpftem Trend, Saisonprofil auf aktuellem Niveau, deren
Kombination, Vorjahresmonat, Mittel der letzten 6 Monate. Mieter, Gäste und sonstige
Verträge werden als feste Größe addiert. Mit den aktuellen Daten: Ø Fehler 1 Monat voraus
≈ 4–9 Personen je Standort.

### Oberfläche

Neu aufgebaut: Seitenleiste statt Tabs, **ein** globaler Standort- und Netto/Brutto-Filter
für alle Seiten, Karten mit KPI-Kacheln und Verlaufslinien, einheitliches Design-System
(Hell, Dunkel, Hochkontrast, System – live umschaltbar ohne Neuaufbau), Diagramme mit
Fadenkreuz-Tooltip, farbfehlsichtigkeits-geprüfte Standortfarben, Toast-Meldungen statt
Dialogfenstern, Laden im Hintergrund mit Fortschrittsbalken, Tastenkürzel (Strg+1…6, F5).

* **Übersicht** – Lage je Standort mit Ampel, Veränderung zur Vorwoche, Verlauf + Prognose,
  Zusammensetzung, nächste Monate, anstehende Anreisen.
* **Belegung** – beliebiger Zeitraum (Schnellwahl, Von/Bis, Monatssprung), Zusammensetzung
  nach Belegungsart, Personentage je Monat, Häuser, Wochentags-/Saisonmuster.
* **Prognose** – Monatsverlauf mit 80/95 %-Band und gesichertem Bestand, Kapazitätscheck mit
  Was-wäre-wenn, Modellvergleich und Blind-Prognosen.
* **Assistent** – Chat (siehe unten).
* **Daten & Import** – Quelle, Kapazitäten, Mieten, Anreisen, manuelle Einträge.

### Assistent

Die Vorversion ließ ein kleines Sprachmodell gleichzeitig die Frage verstehen **und** Zahlen
aus einem Textkontext abschreiben – beides unzuverlässig, der Tab war deaktiviert. Jetzt:

1. **Präzise Datenantworten (immer, offline):** Ein Sprachverständnis für Standorte
   („BP“, „Pyrmont“), Zeitangaben („heute“, „im März“, „Q1 2026“, „letzte 6 Monate“,
   „vom 1.3. bis 15.4.“, „nächste Woche“) und Absichten (Belegung, frei, Auslastung,
   Kapazität, Prognose, Trend, Vergleich, Höchst-/Tiefstwert, Personentage, Anreisen,
   Mieter, Häuser, Modellgüte). Folgefragen („und Goslar?“, „und im Dezember?“) übernehmen
   den Kontext. Jede Zahl wird berechnet, Prognosen werden als solche gekennzeichnet.
2. **Optional KI für freie Fragen** (Einstellungen → KI): Claude (Anthropic API) oder ein
   lokales Modell über Ollama/LM Studio. Das Modell bekommt keine Rohdaten, sondern ruft
   dieselben Abfragefunktionen als Werkzeuge auf – dadurch stammen auch dessen Zahlen aus den
   Berechnungen des Dashboards. Der API-Schlüssel liegt in der Windows-
   Anmeldeinformationsverwaltung (keyring), nicht mehr im Klartext in einer JSON-Datei.
3. Themenfremdes („Erzähl einen Witz“, Rollenwechsel-Versuche) wird abgelehnt.

## Aufbau

```
belegung/            fachlicher Kern ohne Qt (testbar)
  pivot.py           Pivot-Profil, Einlesen per openpyxl oder Excel-COM
  importe.py         Excel/CSV-Listen mit Spaltenerkennung
  datenstand.py      Datenmodell, Aufschlüsselung, Ist+Prognose-Verlauf
  prognose.py        Backtest-Modellauswahl, kalibrierte Bänder
  laden.py           Quelle -> Datenstand
  export.py          JSON für Belegungsdashboard.html (bisheriges Format)
  assistent/         Sprachverständnis, Antworten, Werkzeuge, LLM-Anbindung
  ui/                PySide6-Oberfläche (Theme, Widgets, Diagramme, Seiten, Dialoge)
tests/               pytest
```

## Bekannte Grenzen

* Die Prognose ist ein Monatsmodell; Tageswerte in der Zukunft sind zwischen den
  Monatswerten interpoliert und nie kleiner als der an dem Tag gebuchte Bestand.
* Ob die Anreise-Liste Personen enthält, die bereits in der Pivot als künftiger Bestand
  stehen, lässt sich aus den Dateien nicht erkennen. In der aktuellen Pivot steigt der
  künftige Bestand für Bad Pyrmont und Goslar nie – dort sind Neuaufnahmen also nicht
  enthalten. Bei Weser-Ems gibt es dagegen bereits gebuchte Kurzzeitblöcke (z. B. +20 ab
  05.10.2026). Stehen dieselben Personen auch in der Anreise-Liste, würden sie doppelt
  gezählt – dann Weser-Ems-Zeilen in der Liste weglassen.
* Die Hilfs-Sheets der alten .xlsm (Kapazitaeten, Externe_Belegungen, …) werden nicht mehr
  gelesen; Kapazitäten und Einträge werden in der App gepflegt.
