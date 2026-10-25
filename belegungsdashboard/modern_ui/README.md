# Neue Oberfläche (modern_ui) – Version 0.13.0

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
| **Heute** | alles, was zu tun ist (Karten mit 1-Klick-Lösung), **frei nach Planung** (5 Wochen, gesamt/EMR/Doppel mit Ampel), **neue Personen (7 Tage)**, Anreisen der nächsten 7 Tage, Abreisen, Reinigung, Neuigkeiten |
| **Anreisen** | *Zuteilen* (oben „nach Planung mind. … frei“, Zimmer in der Zeile, grüner Vorschlag, Filter inkl. **neu (7 Tage)**, NEU-Marke, Personenangaben per Klick auf den Namen: Geschlecht, Tier, **Gruppe**, Abreise, Bemerkung, **Abreise-Erinnerung** über Termine/Kalenderdatei/Outlook) · *Personen* (alle kommenden Anreisen auf einer Liste, Filter neu/ohne/mit Zimmer, Suche) · *Abreisen* (heute/morgen/Woche, drucken) · *Firmenprogramm* (was noch einzutragen ist, kopieren, abhaken) · Menü *Mehr*: Anreise-/Schlüsselliste, Zimmerschilder, Person hinzufügen, Planung zurücknehmen, Belegung optimieren, UWT automatisch zuteilen/zurücknehmen, **Zimmerliste als Excel**, **auch vergangene Anreisen** · Firmenprogramm: **Abgehakte ausblenden** |
| **Zimmer** | *Übersicht* (alle Zimmer als Kacheln je Haus und Etage, Tag wählbar, Mängel-Marke, unbewohnbar rot) · ***Karten*** (je Etage eine Spalte, je Zimmer Zustand, Merkmale, Mängel, Bewohner mit Zeitraum, frei bis …) · *Zeitstrahl* (Haus, 2/4/8 Wochen, Klick öffnet die Zimmerkarte) · *Liste* (Suche, Status mit Zahlen, Mängel, Renoviert, Vinyl, Teppich, Tier …, **Filter-Menü**: Boden, Mangel-Stufe/-Art, Renovierung seit, Gästezimmer, Personengruppe, außer Betrieb · **Stichtag** · drucken mit/ohne Namen, **Kopieren für Excel**, **Belegung am Tag als Excel** · Zimmer markieren → **Eigenschaften setzen** (Renovierung, Boden) · **Renovierungsliste einfügen**) · *Zimmerkarte*: **Person hinzufügen** (aus den Anreisen ohne Zimmer oder neu anlegen und gleich einplanen), Bewohner, Zimmer ändern, fest/geplant, Umzug planen/zurücknehmen, Mängel melden/beheben/unbewohnbar, Hinweis, Notizen mit Wiedervorlage, zur Reinigung · *Defekte Zimmer* (nach Dringlichkeit, „behoben“ je Mangel, nächste Anreise, FM-Bericht, FM-Excel, Erledigte aus der FM-Liste übernehmen, für Mail kopieren) |
| **Reinigung** | *Reinigungsliste* (heute/Woche, abhaken, eilige auf einmal, Zimmer hinzufügen, drucken) · **Wochenblatt** zum Aushängen (Woche wählbar, mit/ohne Namen) · *Facility-Checks* |
| **Termine** | *Liste* (fällig, demnächst, erledigt) · *Monat* · eigene Termine anlegen/ändern/löschen |
| **Assistenz** | *Aufträge* in normalen Sätzen (verstehen → prüfen → ausführen, Rückgängig je Auftrag) · *Mails* (einfügen oder aus Outlook, erkennen, Person zuordnen, umsetzen, Posteingang) · *Fragen & Zahlen* (aus den Daten, optional KI) |
| **Mieter** | Verträge, Mail zum Vertragsende (Outlook-Entwurf), *Neuer Mieter* (alle Unterlagen als PDF), *Verlängern* (Nebenabrede Word + PDF), Unterlagen neu erstellen |
| **Auswertung** | *Lage* (heute, Verlauf mit Prognose, **anstehende Anreisen 21 Tage**) · *Belegung* (Zeitraum, Personentage, Ø/Höchst/**Tiefst**, **Ø Auslastung**, **Tagesverlauf nach Belegungsart**, **Personentage je Monat**, **Häuser**, **Wochentags- und Saisonmuster**) · *Prognose* (Monate, 80/95 %-Spannen, **Backtest im Diagramm**, Was-wäre-wenn, Modell, Blind-Prognosen) · *Zimmer & Engpässe* (frei jetzt und nach Planung, EMR/Doppel mit Ampel, Lage) · Standort und Netto/Brutto |
| **Daten & Import** | Anreiselisten, UWT, Gebäudeplan (prüfen und übernehmen), ZKL mit Abgleich, Zimmer-Pivot, Belegungs-Pivot (auch vom Server), Kapazitäten, Mieten/Anreisen für die Statistik, manuelle Einträge |
| **Inventar** | *Gegenstände* (Bestand, verteilt, im Lager, verteilen/entfernen, **wo steht das?** je Haus) · *Zimmer* (Haus, Suche, **nur ohne Ausstattung**, Ausstattung ändern, kopieren) · ***Übersicht je Haus*** · Inventarliste drucken (alle oder je Haus), **Excel** |
| **Einstellungen** | *Allgemein* (Zimmerplanung, Erinnerungen, Engpass-Grenzen, KI mit **Verbindung testen**) · *Zimmer-Stammdaten* · *Sicherung & Verlauf* |

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

## UWTler und Mieter aus echten Daten (neu in 0.13)

* **Der Prognosegraph steht ganz oben.** Darunter folgen Kennzahlen, Erkenntnisse, Szenario und – bei Goslar – die
  Detail-Einheit „UWTler, Mieter und Kontingente“ (mit den Steppern), danach Standortvergleich, Tabelle, Methodik.
* **Schalter direkt über dem Graph:** `[✓] UWTler einbeziehen` und `[✓] Mieter einbeziehen`. Sie wirken auf alles:
  Kurve und Bänder, Kennzahlen (auch „Aktuelle Belegung“ und den Vorjahresvergleich), Reserve, Vorjahr, Tabelle,
  Standortvergleich, Exporte. Ist ein Schalter aus, wird die Gruppe herausgerechnet (Titel: „ohne UWTler“,
  Hinweis „reine Teilnehmer-Sicht“) – so lässt sich die reine Teilnehmer-Belegung mit der Gesamtbelegung vergleichen.
  Bei Bad Pyrmont und Weser-Ems sind die Schalter ausgegraut (dort gibt es keine UWTler und Mieter).
* **Woher die Zahlen kommen:**
  * UWTler: die gebuchten UWT-Blöcke (UWT-Listen) – sie waren schon in der Gesamtbelegung enthalten.
  * Mieter: die **Mietverträge** (Seite „Mieter“) und die Mieter laut **Zimmerplan**, je Person ein Platz von … bis.
    Stehen Mieter zusätzlich in den Belegungslisten, zählt je Tag die größere Zahl – nichts wird doppelt gezählt.
    Bisher fehlten Mieter in der Prognose, wenn es keine Mieten-Liste gab; mit eingeschaltetem Schalter sind sie jetzt
    enthalten. In der Zukunft zählen die Verträge bis zu ihrem Ende (Verlängerungen sind erst nach Eintrag sichtbar).
* **Keine künstlichen Limits mehr in der Tabelle:** Sie zeigt die echten gebuchten Plätze; das Kontingent steht nur
  als „Plan …“ im Spaltenkopf, Überschreitungen sind farbig markiert.

## Prognose für die Geschäftsführung (neu in 0.12)

* **Backtest direkt am Graph:** Schalter „Backtest an/aus“ neben den Reitern *Trend & Prognose · Kapazitätsreserve ·
  Vorjahresvergleich* (nicht mehr im Menü „Optionen“). Jetzt auch für **Gesamt** – als Summe der Standort-Backtests,
  so wie die Gesamtprognose die Summe der Standortprognosen ist.
* **Management-Szenario** statt Schieberegler: Schnell-Pills *Ausgangslage*, *+10 % Auslastung*, *−10 % Auslastung*,
  *Kapazitätskürzung Sanierung* (zieht die Betten der Zimmer ab, die ein offener Mangel derzeit **unbewohnbar** macht –
  Gebäudeplan Goslar; ohne solche Zimmer ist die Pill ausgegraut) und Plus/Minus-Stepper (Kapazität ±1/±10,
  Auslastung ±1/±5 %, bis ± 25 %). Im Graph bleibt die echte Prognose stehen; das Szenario läuft als **orange
  gepunktete Schattenkurve** mit (ggf. mit Schatten-Kapazitätslinie), im Tooltip als „Szenario – Simulation“.
* **Ansicht „Nach Status“** (Schalter neben dem Backtest, im Modus Trend): gestapelte Fläche **UWTler** (Deep Blue) ·
  **Mieter** (Slate) · Teilnehmende & Sonstige. UWT und Mieter stammen aus den Listen (Ist bzw. bereits gebucht), der
  Rest bis zur Gesamtbelegung ist Ist bzw. Prognose – die Unsicherheit liegt also allein bei den übrigen.
* **Goslar · UWTler und Mieter** (seit 0.13 als Detail unter dem Graph, sobald *Goslar* gewählt ist): Balken der
  Kapazität heute (UWT · Mieter · übrige · frei) mit Zahlen und Anteilen, Aussagen zu fest gebundenen Plätzen und
  Kapazitätsrisiko. Dazu **Kontingente** – eine geplante prozentuale Aufteilung der Kapazität (UWT %, Mieter %, Rest
  für Teilnehmende & Sonstige) mit Steppern. Je Monat wird geprüft, ob die gebuchten UWT-/Mieterplätze und die
  Prognose der übrigen in ihr Kontingent passen (orange ≥ 90 %, rot überschritten). Ohne eigene Eingabe gilt ein
  Vorschlag aus den Daten (höchster gebuchter Anteil der nächsten 12 Monate). Die Kontingentgrenzen erscheinen auch
  im Status-Graph. Kontingente sind eine Planungsannahme, gespeichert in `modern_ui.json` – Kapazität und Belegungsdaten
  bleiben unverändert. In der Präsentation erscheint eine Kurzfassung.

## Prognose als Executive-Ansicht (neu in 0.11, ersetzt die Prognose-Ansicht aus 0.10)

*Auswertung → Prognose* ist jetzt von oben nach unten nach Wichtigkeit aufgebaut:

1. **Fünf KPI-Karten** – jede mit Wert, Einheit, Bezugszeitraum, Vergleich und Ampel (Mauszeiger: Erklärung):
   *Aktuelle Belegung* (Stichtag, Vergleich: gleicher Wochentag vor 52 Wochen), *Prognose Belegung* (nächster voller
   Monat, 80 %-Band, Vergleich: Ist desselben Monats im Vorjahr), *Freie Reserve* (Kapazität − erwartet, dazu der
   ungünstige Fall und der knappste Monat), *Kapazitätsrisiko* (Monate, deren obere 80 %-Grenze „kritisch“ erreicht),
   *Prognosegüte* (Ø-Fehler im Backtest, Trefferquote des 80 %-Bands).
2. **Erkenntnisse** – automatisch aus den Daten, jede Zeile markiert als **Fakt** (gemessen), **Prognose** (Modell),
   **Einschätzung** (Ampel-Regel) oder **Hinweis**. Es wird nichts erfunden: fehlt ein Vorjahreswert, entfällt die Aussage.
3. **Prognosegraph** mit drei Modi für drei Fragen:
   * *Trend & Prognose* – „Wohin entwickelt sich die Belegung?“ Ist durchgezogen, laufender Monat als hohler Punkt
     (unvollständig), Prognose gestrichelt, 80/95 %-Band dezent, Kapazität rot gestrichelt, Übergang „Prognose →“.
     Die Achse bleibt fest, damit nichts springt.
   * *Kapazitätsreserve* – „Wie viel Luft bleibt?“ Balken = Kapazität − erwartet (grün / orange knapp / rot kritisch;
     Ist-Monate blass), Linie = ungünstiger Fall (Kapazität − obere 80 %). Negative Werte liegen sichtbar unter der
     Nulllinie „Kapazitätsgrenze“.
   * *Vorjahresvergleich* – „Wie steht es gegenüber dem Vorjahr?“ 12 Kalendermonate (6 zurück, 6 voraus) gegen dieselben
     Monate ein und zwei Jahre früher (Ist); Abweichung im Tooltip; fehlende Monate bleiben Lücken.
   Der Graph baut sich **nur beim ersten Öffnen** auf (nicht bei jedem Filterwechsel), *Aufbau abspielen* wiederholt das
   bewusst; unter *Optionen* abschaltbar. Ist im System „Bewegung reduzieren“ eingestellt, gibt es keine Animation.
4. **Szenario (Simulation)** – seit 0.12 als Management-Szenario (siehe oben): Pills und Stepper, Auslastung ± 25 %. Daneben **Ausgang gegen Szenario**
   (Kapazität, Höchststand, kleinste Reserve, Risikomonate). Ein aktives Szenario ist orange schraffiert und mit
   „SIMULATION – keine echten Daten“ markiert, ebenso Graphtitel, KPIs und Tabelle. Es wird nichts gespeichert,
   die echten Daten bleiben unberührt. Weitere Stellschrauben (z. B. Verweildauer) gibt es bewusst nicht – dafür fehlt
   ein belastbares Modell.
5. **Standortvergleich** – Auslastung heute und Spitze der nächsten 12 Monate je Standort in festen Standortfarben
   (wie im Hauptprogramm), Tabelle mit Reserve und Ø-Fehler; Klick auf einen Standort zeigt ihn im Graph.
6. **Monate im Detail** – *Kompakt* (Monat, Erwartet, 80 %-Band, Reserve, Einschätzung) oder *Alle Spalten*
   (+ 95 %-Band, Gebucht, Reserve ungünstig). Die Spaltenköpfe erklären sich beim Überfahren.
7. *So wurde gerechnet* und *Backtest* wie bisher.

**Begriffe:** *Gebucht* (im Hauptprogramm „gesichert“) ist der heute schon bekannte Bestand: Teilnehmende mit geplantem
Ende + Verträge; die Prognose fällt nie darunter. Im laufenden Monat gilt *Gebucht* nur für die restlichen Tage
(markiert mit *), *Erwartet* für den ganzen Monat. *Reserve* = Kapazität − erwartet; *Reserve ungünstig* =
Kapazität − obere 80 %-Grenze.

**Präsentation** (Knopf oben rechts oder Taste **P**): Navigation, Leisten und Werkzeugleiste verschwinden; vier große
KPIs, der Graph groß, Datenstand und Netto/Brutto im Kopf, Standort umschaltbar, Standortvergleich zuschaltbar,
Vollbild. Im Trend-Modus **schrittweiser Aufbau** mit ← / →: 1 Ist · 2 Prognose · 3 Unsicherheit · 4 Kapazität.
**Esc** beendet.

**Export** (oben rechts): *Diagramm als PNG* (hochauflösend, mit Titel, Zeitraum und Stand), *Executive Summary* als
Druckansicht / PDF (KPIs, Erkenntnisse, Monate, Standorte), *Prognosedaten* als Excel oder CSV – jeweils mit dem
gewählten Standort, Netto/Brutto, Zeitraum und Szenario.

**Zimmer-Übersicht:** Die Legende ist entfallen – die Kacheln oben tragen dieselben Symbole und Farben wie die Zimmer
und zählen: frei (Zimmer mit mindestens einem freien Bett; Doppelzimmer mit nur einem freien Bett sind grün umrandet
und werden in der Kachel genannt, wenn es welche gibt), belegt, geplant, gesperrt, mit Mängeln und neu **unbewohnbar**
– jede Kachel filtert per Klick.

## Darstellung: Layout × Theme (neu in 0.9)

**Werkzeugleiste unten rechts** (blendet sich nach kurzer Zeit auf einen Griff zurück; Griff anklicken = angeheftet):
Layout · Theme · Hell/Dunkel · Dichte · Suchen/Prompt · Vollbild · Notiz · **Original-Zustand** (roter Knopf, 1 Klick).
Dieselbe Wahl unter *Einstellungen → Allgemein → Darstellung*. Wirkt sofort ohne Neuladen und bleibt gespeichert
(`modern_ui.json` im Datenordner – auch die Notiz).

**Ebene 1 – Layout (Aufbau)**

| Layout | Aufbau |
|---|---|
| **Original-Zustand** | bisheriges Design und Layout, unverändert (Standard) |
| **Classic Enterprise Grid** | Seitenleiste, einklappbar auf Symbole mit Tooltips (Strg+B), volle Datendichte |
| **AI-Canvas & Prompt** | zentrale Eingabe oben (Strg+K oder /, Esc leert): versteht z. B. „freie Zimmer Haus 2“, „ohne Zimmer“, „neu“, „EMR nächste Woche“, „Mängel unbewohnbar“, „Abreisen diese Woche“, Namen, Zimmernummern – Antworten erscheinen live als Karten (Kennzahlen, Personen, Zimmer, Abreisen); Klick öffnet Zimmerkarte/Zuteilen, „Alle als Liste“ übernimmt die Filter |
| **Showcase** | schwebendes Dock oben (alle Seiten, „Verwalten ▾“), große Titel, Kennzahl-Kacheln, Karten mit Glas, viel Weißraum |

**Ebene 2 – Theme (nur Farben/Schrift), in jedem Layout:** Original · inn-tegrativ (#183861) · Linear Monochrome ·
Executive Obsidian (Bronze/Champagner) · Soft Nordic (Slate/Sand) – jeweils **hell und dunkel** (Original-Farben nur
dunkel). Dazu **Dichte** normal/kompakt. Dialoge mit Milchglas-Hintergrund, Menüs als Glas-Popover, Tabellen mit
festem Kopf, gedeckte Status-Badges.

Technik: Ohne Klassen am `<body>` gilt ausschließlich das bisherige CSS; alles Neue hängt an `body.pro` (+ `lay-…`,
`th-…`, `mod-…`, `dichte-…`). Ein Test prüft das für jede Regel; der Bildvergleich aller 29 Ansichten zeigt den
Original-Zustand pixelgleich zu 0.7 – bis auf die Werkzeugleiste, die Versionsnummer, die Zahlen in der Zimmer-Legende
und den Block „Darstellung“. Aus 0.8 übernommen: „Corporate“ → inn-tegrativ, „Bento“ → Obsidian, „Editorial“ → Nordic,
„Navigation oben“ → Showcase.

**Neu in 0.7:** Zimmer-*Karten* mit allen Details, Person direkt im Zimmer hinzufügen, Filter „neu (7 Tage)“ und
die restlichen Funktionen des bisherigen Programms (fett in der Tabelle oben).
*Neu* heißt: zum ersten Mal in den Listen. Das Hauptprogramm speichert dafür kein Datum – die neue Oberfläche merkt
es sich ab jetzt selbst (`modern_ui_neu.json` im Datenordner). Beim allerersten Start gelten Personen aus Listen als
neu, die in den letzten 7 Tagen importiert wurden.

### Gegenüber dem bisherigen Programm

* PDFs (Mietunterlagen, Nebenabrede) erstellt hier Microsoft Edge im Hintergrund; ohne Edge wird der Mietvertrag als
  HTML gespeichert und zum Drucken geöffnet. Ablage: zuletzt genutzter Export-Ordner bzw. `Mietunterlagen` im Datenordner.
* Drucken öffnet eine Druckansicht im Browser (drucken oder als PDF speichern).
* Statistik-Listen (Mieten/Anreisen) werden mit automatischer Spaltenzuordnung gelesen; passt sie nicht, bitte
  einmal im Hauptprogramm mit Spaltenwahl importieren – danach merkt sich das Programm die Zuordnung.
* „Neu vorschlagen (eigene Änderungen verwerfen)“ entfällt: Hier wird jede Zuteilung sofort gespeichert – zurück
  geht es mit „Rückgängig“ bzw. Strg+Z.
* Nicht übernommen (gehört zum Fenster des Hauptprogramms): Tabs/neues Fenster, Start mit Windows im Infobereich,
  Name des Dashboards.
* Darstellung (Designs, hell/dunkel) gibt es hier nicht – die neue Oberfläche ist bewusst ein ruhiges dunkles Design.

## Aufbau

| Datei | Inhalt |
|---|---|
| `app.py` | Start (Fenster bzw. Edge), Protokoll `modern_ui.log` |
| `modern/oberflaeche.py` | Rahmen (Seitenleiste, Kopf, Panel rechts, Hinweis mit Rückgängig, Tasten) und Zuteilen |
| `modern/register.py` | Gliederung: Seiten, Reihenfolge, Gruppen |
| `modern/seite_*.py`, `modern/seiten.py` | die Seiten |
| `modern/*_kern.py`, `modern/kern.py` | Daten und Änderungen über das Hauptprogramm, ohne Oberfläche – testbar |
| `modern/seite_prognose.py`, `modern/analytik_kern.py` | Prognose als Executive-Ansicht: Darstellung bzw. KPIs, Erkenntnisse, Vergleiche (ohne Oberfläche, testbar) |
| `modern/stil.py` | Farben und Stil, alle Farbwerte nur hier |
| `tests/` | Tests mit erfundenen Namen: `python -m pytest modern_ui/tests` |

## Rückgängig machen / entfernen

Den Ordner `modern_ui` löschen genügt – das bisherige Programm und seine Daten bleiben. Sicherungen: vor 0.1.0
`backup/v6.28.0`, vor 0.2.0 `backup/modern-0.1.0`, vor 0.3.0 `backup/modern-0.2.0`, vor 0.4.0 `backup/modern-0.3.0`, vor 0.5.0 `backup/modern-0.4.0`, vor 0.6.0 `backup/modern-0.5.0`, vor 0.7.0 `backup/modern-0.6.0`, vor 0.8.0 `backup/modern-0.7.0`, vor 0.9.0 `backup/modern-0.8.0`, vor 0.10.0 `backup/modern-0.9.0`, vor 0.11.0 `backup/modern-0.10.0`, vor 0.12.0 `backup/modern-0.11.0`, vor 0.13.0 `backup/modern-0.12.0` (jeweils auch als Zip in `Sicherung`).
