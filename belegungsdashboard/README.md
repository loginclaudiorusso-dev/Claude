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
python -m pytest tests                         # Tests für Pivot, Prognose, Importe, Assistent, Export
pyinstaller belegungsdashboard_gui.spec        # dist/Belegungsdashboard.exe + dist/Belegungsdashboard-Export.exe
```

Einstellungen und lokale Listen liegen wie bisher neben der exe
(`kapazitaeten_manuell.json`, `manuelle_eintraege.json`, `pivot_profile.json` werden
weiterverwendet; neu: `einstellungen.json`, Ordner `importe/` und `erinnerungen/`). Mit der Umgebungsvariable
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

### Anreisen Internat Goslar (neu)

Unter **Daten & Import → Anreisen Internat Goslar** eine oder mehrere Anreiselisten (.xlsx) auf
einmal hochladen. Erkannt wird das bekannte Format „Anreiseliste TT-MM-JJJJ“ (auch mit „EMR“ im
Titel); die Spalten dürfen von Liste zu Liste abweichen. Übernommen werden nur **Name, Maßnahme,
Anreise (aus dem Titel), Internat ja/nein** und – falls vorhanden – TN-ID und Abreise.

* Zur Belegung zählen nur Personen mit Internat „ja“, und zwar **ab dem Tag nach dem Stichtag**
  (vergangene Tage stehen bereits in der Pivot).
* Personen werden über die TN-ID wiedererkannt: ein erneuter Upload aktualisiert die Liste,
  eingetragene Abreisen und Erinnerungen bleiben erhalten. Wer nicht mehr auf der Liste steht,
  wird entfernt.
* **Abreise und Erinnerung** per Doppelklick bzw. Stift-Symbol eintragen; Personen ohne Liste über
  „Person hinzufügen“. Erinnerungswege (Vorgabe unter Einstellungen → Erinnerungen):
  * **Outlook-Termin** am Abreisetag mit Erinnerung X Tage vorher – erinnert auch, wenn das
    Dashboard geschlossen ist,
  * **E-Mail an mich**, die Outlook zeitversetzt am Erinnerungstag verschickt,
  * **Kalenderdatei (.ics)** oder **nur im Dashboard** (Hinweis beim Start und auf der Übersicht,
    mit „Erledigt“ quittieren).
  Wird die Abreise geändert oder die Person gelöscht, wird der Outlook-Eintrag mit angepasst.
* Ohne Abreise zählt eine Person nur als Termin – oder mit einer einstellbaren Standarddauer.

### UWT (neu)

PDF „UWT An- und Abreiseliste“ hochladen: Klassen, Anzahl und Zeitraum je Block („''“ = wie
darüber) sowie, falls aufgeführt, die Personen mit Zimmer. Die UWT steht nicht in der Pivot und
zählt deshalb über den ganzen Block zur Belegung Goslar (Kategorie UWT).

### Zimmerplan Goslar (neu)

Eigene Seite **Zimmerplan** (Strg+5). Grundlage ist der **Gebäudeplan** als Word-Export
(.docx) aus dem Belegungssystem – regelmäßig neu importieren. Daraus kommen Zimmer, Betten,
Belegungen mit Zeitraum, Sperrungen/Renovierungen und Zimmerfreigaben („Frei teilw.“).
Die 17 Gästezimmer (Haus 2, Etage 6, 601–617) sind fest hinterlegt.

**Zuteilen:** Anreise wählen → das Programm schlägt für jede Person ein Zimmer vor;
Zimmer, Geschlecht und Tier lassen sich je Person ändern, dann „Übernehmen“. Übernommene
Zuweisungen zählen bei späteren Vorschlägen als belegt, bis die Person im Gebäudeplan steht.
**Excel-Zimmerliste**: Zimmerliste je Anreise, Übersicht je Flur (für Vorbereitung und
Reinigung) und freie Zimmer am Anreisetag – druckfertig (A4 quer).

Feste Regeln:

| Gruppe | erlaubt |
|---|---|
| EMR | nur Haus 2, Etage 1–2 |
| Gäste | nur Gästezimmer Haus 2, Etage 6 |
| Mieter | nur Haus 6 |
| UWT | Haus 3.2, 3.3 und 6 |
| RVL | Haus 3.1 |
| Assessment, RVT, Reha-Maßnahmen | Haus 2 (Etage 1–5), 3.1, 3.2, 3.3 – nicht Haus 6 |

* Tiere nur in Haus 3.1 EG/UG · Zimmer mit Bad über den Flur (Haus 6: x01, x02, x05, x08,
  x09) nur Männer · Doppelzimmer teilen sich nur Personen derselben UWT-Klasse und desselben
  Geschlechts, alle anderen wohnen allein darin · nach jeder Abreise ein Tag Puffer
  (einstellbar).
* Wünsche: eine Anreise zusammen auf einem Flur (Flure = durch das Treppenhaus getrennte
  Hälften), Zimmer möglichst nicht direkt nebeneinander · kurze Maßnahmen und Assessment
  bevorzugt Haus 2 Etage 5 · Doppelzimmer für die UWT, Tier-Zimmer und Haus 2 Etage 1–2 (EMR)
  möglichst freihalten.
* Widersprechen sich Regeln (z. B. EMR mit Tier), bleibt die Person unzugeteilt und der Grund
  wird angezeigt – dann von Hand festlegen.
* Geschlecht steht in den Listen nicht; es wird aus dem Vornamen geschätzt (mit * markiert)
  und lässt sich korrigieren. Tiere werden aus den Bemerkungen erkannt („Hund“, „Katze“ …);
  Bemerkungen, die später kommen, unter Daten & Import an der Person ergänzen.
* Ohne Abreise wird eine übliche Dauer angenommen (EMR/Assessment 4 Wochen, RVL/RVT 13,
  sonst 52) und mit ≈ gekennzeichnet.

**Häuser:** alle Zimmer je Haus, Etage und Flur mit Status an einem frei wählbaren Tag
(frei, teilweise, belegt, geplant, gesperrt), Tooltip mit Bewohnern und „frei bis“.

**Zimmer-Stammdaten:** Flur, Betten, Bad über den Flur, Tier-Zimmer, Gästezimmer und „im
Internat“ (z. B. Etagen der Jugendhilfe ausblenden) – aus den Grundrissen vorbelegt, bitte
einmal prüfen. Gespeichert werden nur Abweichungen (`zimmer_stammdaten.json`).

### Mieten

Excel-/CSV-Liste mit automatischer Spaltenerkennung („Mietbeginn“, „Einrichtung“, „Anzahl
Betten“, „Mieter / Firma“ …), Vorschau vor dem Import, Zuordnung je Dateiname gemerkt. Mieten
ohne Ende gelten als unbefristet, leerer Standort = Goslar.

### Datenschutz

Personennamen bleiben lokal: Der HTML-Export und die optionale KI-Anbindung bekommen statt des
Namens nur die Maßnahme bzw. Klasse.

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
  importe.py         Excel/CSV-Listen mit Spaltenerkennung (Mieten)
  anreiseliste.py    Anreiselisten Goslar, Abreisen, fällige Erinnerungen
  uwt.py             UWT-PDF (Blöcke und Personen)
  erinnerung.py      Outlook-Termin/-Mail, .ics
  gebaeudeplan.py    Gebäudeplan (.docx): Zimmer, Belegungen, Sperrungen
  zimmerplan.py      Zimmer-Stammdaten, Regeln, Zuteilungsvorschlag
  zimmerexport.py    Excel-Zimmerliste
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
