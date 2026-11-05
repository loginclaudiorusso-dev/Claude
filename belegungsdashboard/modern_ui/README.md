# Neue Oberfläche (modern_ui) – Version 0.62.0

Eine neue, ruhige Oberfläche für das ganze Programm. Sie liegt im eigenen Ordner `modern_ui` und **ändert keine
Datei des bisherigen Programms**. Daten und Regeln kommen aus dem Hauptprogramm im Ordner darüber (`belegung`):
dieselben Dateien, dieselben Zuteil-Regeln, dasselbe Rückgängig. Beide Programme zeigen denselben Stand.

## Starten

**Neu ab 0.54 – gemeinsamer Netzwerkordner:** Das Paket `INNternat.zip` in den Netzwerkordner entpacken und
`INNternat starten.bat` doppelklicken (Einzelheiten unten und in `LIESMICH.txt` im Paket).

Bisherige Einzelplatz-Installation: Das Update-Zip wie immer nach `INNternat` entpacken, dann `INNternat\modern_ui\Start.bat`. Beim ersten Start
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
| **Zimmer** | *Übersicht* (alle Zimmer als Kacheln je Haus und Etage, Tag wählbar, **mehrere Kacheln kombinierbar**, **Mangelart-Filter**, Mängel-Marke, unbewohnbar rot) · ***Karten*** (je Etage eine Spalte, je Zimmer Zustand, Merkmale, Mängel, Bewohner mit Zeitraum, frei bis …) · *Zeitstrahl* (Haus, 2/4/8 Wochen, Klick öffnet die Zimmerkarte, geplante Personen per Ziehen verschieben) · *Liste* (Suche, Status mit Zahlen, Mängel, Renoviert, Vinyl, Teppich, Tier …, **Filter-Menü**: Boden, Mangel-Stufe/-Art, Renovierung seit, Gästezimmer, Personengruppe, außer Betrieb · **Stichtag** · drucken mit/ohne Namen (auch in der Übersicht je Kachel), **Excel mit „frei bis“**, **Kopieren für Excel**, **Belegung am Tag als Excel** · Zimmer markieren → **Eigenschaften setzen** (Renovierung, Boden) · **Renovierungsliste einfügen**) · *Zimmerkarte*: **Person hinzufügen** (aus den Anreisen ohne Zimmer oder neu anlegen und gleich einplanen), Bewohner, Zimmer ändern, fest/geplant, Umzug planen/zurücknehmen, Mängel melden/beheben/unbewohnbar, Hinweis, Notizen mit Wiedervorlage, zur Reinigung · *Defekte Zimmer* (nach Dringlichkeit, „behoben“ je Mangel, nächste Anreise, FM-Bericht, FM-Excel, Erledigte aus der FM-Liste übernehmen, für Mail kopieren) |
| **Reinigung** | *Reinigungsliste* (heute/Woche, abhaken, eilige auf einmal, Zimmer hinzufügen, drucken) · **Wochenblatt** zum Aushängen (Woche wählbar, mit/ohne Namen) · *Facility-Checks* |
| **Termine** | *Liste* (fällig, demnächst, erledigt) · *Monat* (Klick auf einen Tag = neuer Termin, Klick auf einen Eintrag = öffnen) · eigene Termine anlegen/ändern/löschen |
| **Assistenz** | *Aufträge* in normalen Sätzen (verstehen → prüfen → ausführen, Rückgängig je Auftrag) · *Mails* (einfügen oder aus Outlook, erkennen, Person zuordnen, umsetzen, Posteingang) · *Fragen & Zahlen* (aus den Daten, optional KI) |
| **Mieter** | Verträge, Mail zum Vertragsende (Outlook-Entwurf), *Neuer Mieter* (alle Unterlagen als PDF), *Verlängern* (Nebenabrede Word + PDF), Unterlagen neu erstellen |
| **Auswertung** | *Lage* (heute, Verlauf mit Prognose, **anstehende Anreisen 21 Tage**) · *Belegung* (Zeitraum, Personentage, Ø/Höchst/**Tiefst**, **Ø Auslastung**, **Tagesverlauf nach Belegungsart**, **Personentage je Monat**, **Häuser**, **Wochentags- und Saisonmuster**) · *Prognose* (Monate, 80/95 %-Spannen, **Backtest im Diagramm**, Was-wäre-wenn, Modell, Blind-Prognosen) · *Zimmer & Engpässe* (frei jetzt und nach Planung, EMR/Doppel mit Ampel, Lage) · Standort und Netto/Brutto |
| **Daten & Import** | Anreiselisten, UWT, Gebäudeplan (prüfen und übernehmen), ZKL mit Abgleich, Zimmer-Pivot, Belegungs-Pivot (auch vom Server), Kapazitäten, Mieten/Anreisen für die Statistik, manuelle Einträge |
| **Inventar** | *Gegenstände* (Bestand, verteilt, im Lager, verteilen/entfernen, **wo steht das?** je Haus) · *Zimmer* (Haus, Suche, **nur ohne Ausstattung**, Ausstattung ändern, kopieren) · ***Übersicht je Haus*** · Inventarliste drucken (alle oder je Haus), **Excel** |
| **Einstellungen** | *Allgemein* (Zimmerplanung, Erinnerungen, Engpass-Grenzen, KI mit **Verbindung testen**) · *Zimmer-Stammdaten* · *Sicherung & Verlauf* |
| **Steuerung** (Leitung, ganz unten) | *Cockpit* · *Vorhaben* · *Zeitplan & Kapazität* · *Finanzen* · *Grundlagen* · Entscheidungsvorlage (PDF) – siehe „neu in 0.46“ |

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

## Leitstand-Workbench – zweite Oberfläche zum Umschalten (neu in 0.62)

Ein komplett anders aufgebauter Bildschirm (eigener DOM-Baum, `modern/leitstand_ui.py`), umschaltbar je PC über den
Knopf in der Kopfzeile bzw. „⇄ Ansicht wechseln“ oder **Strg+Umschalt+L**. Gleiche Daten und Handlungen: `Leitstand`
ist eine Unterklasse von `Ansicht` – Speichern über `aendern`/`kern._schritt` (Schreibsperre), Verlauf, Rückgängig.

* **Kommandobrücke (40 px):** vier Bühnen [1] Disposition · [2] Akten & Post · [3] Radar & Prognose · [4] Bau & Budget
  (Tasten 1–4), Live-Omnibar (filtert beim Tippen; `/` oder Strg+K; Enter: Zimmer bzw. Person öffnen, ein Auftrag mit
  mehreren Wörtern geht an die Assistenz), Stand, **Rückgängig im Klartext** („↶ Rückgängig: Erika → 2-204“),
  📌 Abtipp-Modus, ⇄ Ansicht wechseln.
* **Bühne Disposition, drei Spalten:** links der Arbeitsstrom (3 Zahlen: dringend · ohne Zimmer · Reinigung; Sofort
  klären, Anreisen mit Badges m/w und „?“ bei Schätzung, Tier, EMR, Allergie, NEU; Zur Info – mit ↑ ↓); in der Mitte die
  **Gebäude-Matrix** je Haus und Etage (Zellen mit Status, Bewohner, Mangel „!“, Abreise ↗) mit Ebenen Belegung ·
  Abreisen 7 Tage · Mängel und den Umschaltern Etagen · Zeitstrahl · Reinigung. Ist links eine Person gewählt, leuchten
  die passenden Zimmer, der Vorschlag hat einen grünen Rahmen, unpassende sind abgeblendet – **Klick weist zu** (nur
  freie, passende; Gästezimmer weiter nur von Hand), **Enter** nimmt den grünen Vorschlag. Rechts der **Inspektor**: Person
  (Vorschläge mit Begründung, Hinweis bei geschätztem Geschlecht, Warnung „Allergiker + Mangel“), Zimmer (die volle
  Zimmerkarte), Aufgabe – und **alle Formulare** der bisherigen Oberfläche, fest angedockt statt Schiebe-Panel, mit gelbem
  Rahmen „Ungespeichert“.
* **Bühnen 2–4:** links die Arbeitslisten (Firmenprogramm, Mieter, Termine, Assistenz, Personen, Abreisen, Inventar,
  Daten & Import, Einstellungen bzw. Lage, Prognose, Maßnahmen, Engpässe bzw. die Bereiche der Steuerung), in der Mitte
  das bestehende Werkzeug, rechts der Inspektor. Die Reiter der Seiten stehen nur links (nicht doppelt).
* **Tastenleiste (26 px)** mit den gültigen Kürzeln, „?“ zeigt alle.
* **Corporate Design:** PT Sans, Petrol #134F4F/#007F7F/#009A9B, Orange #EF7D00, Grau #5E6E6E, Grund #F4F6F5. PT Sans
  wird aus `Daten\Vorlagen` genommen, wenn die Schriftdateien dort liegen (z. B. `PTSans-Regular.ttf`,
  `PTSans-Bold.ttf`), sonst die installierte Schrift bzw. Segoe UI.
* **Noch nicht im Leitstand:** Zimmertausch in einem Schritt, Beurlaubung, Drag-Vorschau im Zeitstrahl,
  Abgleich-Diff, die flache „Planen“-Maske (Bühne 4 zeigt bis dahin die bisherige Steuerung) – das sind neue Funktionen,
  nicht nur Oberfläche.

## Sperre früher beenden, Zimmer trotzdem nehmen, Vertragsjahr (neu in 0.61)

* **Früher frei (fertig renoviert):** Ist ein Zimmer laut Gebäudeplan noch gesperrt, wird aber früher fertig, steht in
  der Zimmerkarte unter *Sperre* „Fertig renoviert – frei ab …“ – mit Haken „Ich habe geprüft …“. Die Sperre endet dann
  am Vortag; Planung, Suche, Auslastung und Mietverträge sehen das Zimmer ab dem Tag als frei. „Zurücknehmen“ stellt
  den Stand laut Gebäudeplan wieder her. Ablage `modern_sperre_ende.json` (mit gesichert), Verlauf, Rückgängig. Der
  Gebäudeplan und das bisherige Programm bleiben unverändert.
* **Zimmer trotzdem nehmen:** Passt ein Zimmer laut Plan nicht (gesperrt, belegt …), lehnen „Neuer Mieter“ und
  „Vertrag bearbeiten“ es mit Grund ab. Mit dem Haken „Zimmer trotzdem nehmen … ich habe es geprüft“ wird es trotzdem
  übernommen; im Verlauf steht „Zimmer trotz Hinweis gewählt“ mit dem Grund.
* **Jahr der Vertragsnummer:** Die Nummer beginnt immer mit dem Jahr des Vertrags – dem Jahr, in dem er erstellt wird,
  oder dem Jahr des Mietbeginns, wenn das später ist (im Dezember 2026 für Januar 2027 → „27-…“). Der Vorschlag folgt
  dem Mietbeginn; eine Nummer mit falschem Jahr wird abgelehnt.
* **Vertragsnummer nachträglich ändern:** In „Vertrag bearbeiten“ ist die Nummer jetzt änderbar; passt sie nicht zum
  Vertragsjahr, gibt es einen Hinweis mit Vorschlag zum Übernehmen. Zimmerplan und Kennzeichen „flexibel“ ziehen mit,
  die Unterlagen werden mit der neuen Nummer erstellt (alte Dateien bleiben liegen).

## Mietvertrag bearbeiten (neu in 0.60)

* *Mieter* → Stift-Symbol in der Zeile: **Vertrag bearbeiten**. Änderbar sind Anrede, Name, Zimmer, Mietbeginn und
  -ende, Miete, Fläche, Schlüssel, Kaution, E-Mail und „flexibel“; die Vertragsnummer bleibt.
* Das Zimmer-Auswahlfeld zeigt die passenden Zimmer im Zeitraum (das eigene blockiert sich nicht); ein belegtes oder
  unpassendes Zimmer wird beim Speichern abgelehnt – mit Grund.
* Der Zimmerplan zieht mit, im Verlauf steht je Änderung „vorher → nachher“, Rückgängig wie immer. Auf Wunsch werden
  die Unterlagen (PDF) gleich neu erstellt. Wird das Ende geändert, ist die Mail zum Vertragsende wieder offen.

## Mieter ohne Männer-Regel (neu in 0.59)

* Zimmer mit Bad über den Flur (Haus 6) sind weiter nur für Männer – **außer für Mieter**: Mieterinnen dürfen dort
  wohnen, auch wenn das Geschlecht unbekannt ist. Alle übrigen Regeln (Mieter nur Haus 6, belegt/gesperrt …) gelten.
* Die Rückfrage „Geschlecht unbekannt/geschätzt – bitte prüfen“ entfällt bei Mietern im Einzelzimmer.
* Umgesetzt in `modern/regeln_kern.py` (Abschnitt „0.59“): Die Prüfung `passt`, die Erklärung „warum kein Zimmer“ und
  der Vorschlag des Hauptprogramms werden zur Laufzeit ergänzt – `belegung/zimmerplan.py` bleibt unverändert. Das
  bisherige PySide-Programm kennt die Ausnahme deshalb nicht.

## Werte im Diagramm, Rückwärtstest je Welle, Live-Suche, Tasten (neu in 0.58)

* **Maßnahmen-Diagramm ablesbar:** Beim Darüberfahren je Welle Ist bzw. erwartet, schon gebucht, 80-%- und 95-%-Band
  in Personen; an den Prognosepunkten stehen die Werte (bei bis zu 3 Linien).
* **Rückwärtstest im Diagramm** (gepunktet): was das Verfahren für jede vergangene Welle damals geschätzt hätte, mit der
  damals bekannten Spanne (nur aus Fehlern früherer Wellen) – und ob das Ist im 80-/95-%-Band lag. Darunter und in der
  Verfahrenstabelle: „im 80-%-Band x von y“ – ideal etwa 80 % bzw. 95 %.
* **Spannen korrigiert:** Die Fehler werden jetzt relativ zur Schätzung gemessen (vorher zum Ist – die Bänder lagen
  dadurch leicht schief und waren zu eng); bei wenigen Testwerten werden sie geweitet (80 %: 1 + 2,5/n, 95 %: 1 + 8/n).
* **UWT** ist in den Maßnahmen ausgeblendet (eigene Planung); bei Bedarf unter „Ausgeblendete Maßnahmen“ zurückholen.
* **Live-Suche** in Zimmer-Liste, Anreisen → Personen und Inventar: sucht beim Tippen (kurz innehalten genügt), der
  Cursor bleibt im Feld. Enter geht weiter.
* **Ein-Tasten-Kürzel** (nie in Eingabefeldern): *Postfach* L = Aufgabe lösen, S = später, ↑ ↓ wählen. *Abtipp-Modus*
  1–6 = Feld kopieren, E = eingetragen, N oder → = überspringen, ← = zurück. Die Tasten stehen jeweils darunter.

## Neuanmeldungen mit 80-%- und 95-%-Spanne (neu in 0.57)

* Jede erwartete Startwelle hat zwei Spannen: mit 80 % bzw. 95 % Wahrscheinlichkeit liegen die Neuanmeldungen darin.
  Berechnet aus den Fehlern des Rückwärtstests (10.–90. bzw. 2,5.–97,5. Perzentil); bei weniger als 40 Testwerten
  wird die 95-%-Spanne aus der 80-%-Spanne hochgerechnet (× 1,96 / 1,28) – die äußersten Fehler wären sonst Zufall.
  Schon Begonnene und Gebuchte sind die Untergrenze.
* **Diagramm „Je Maßnahme“:** innen 80 %, außen 95 % als Band um die gestrichelte Linie (bei „Ein Diagramm“ nur, wenn
  eine Maßnahme gewählt ist – sonst unlesbar).
* **Tabelle für den Wirtschaftsplan:** Umschalter „Spanne 80 % | 95 %“, beide Spannen im Tooltip; die Summenzeile zeigt
  ebenfalls eine Spanne – schmaler als die Summe der Einzelspannen, weil sich Abweichungen teils ausgleichen.
* **Kennzahl „Erwartet <Jahr>“:** mit 80-%- und 95-%-Spanne.

## Maßnahmen: Neuanmeldungen je Startwelle für den Wirtschaftsplan (neu in 0.56)

*Auswertung → Maßnahmen* zeigt nicht mehr den Bestand (eine zweijährige Maßnahme trägt zwei Jahrgänge übereinander),
sondern wie viele **neu** beginnen – alle Teilnehmenden, Pendler und Internat.

* **Startwellen statt Kalender-Halbjahr:** Winterstart = November bis April (zählt zum Jahr des Januars), Sommerstart =
  Mai bis Oktober. So liegen Januar- und Juni-Starts getrennt (ein Halbjahr Jan–Jun hätte beide zusammengeworfen).
* **Neuanmeldung** = wer in den ersten 6 Wochen eines Kurses dabei ist (Nachrücker zählen mit).
* **Verfahren per Rückwärtstest:** Vier einfache Verfahren – wie Vorjahr, Mittel der letzten 3 Jahre, gewichtetes
  Mittel, gedämpfter Trend – werden an den eigenen Daten geprüft (jede vergangene Startwelle mit mindestens zwei
  Vorjahren, nur mit dem Wissen von damals, über die Hauptmaßnahmen). Das mit dem kleinsten mittleren Fehler wird
  verwendet; von Hand umstellbar. Angezeigt: mittlerer Fehler und Neigung (eher zu hoch/zu niedrig).
* **Künftige Wellen:** schon gebuchte Starts zählen fest, dazu die erwartete Nachbuchung (Buchungskurve wie 0.55);
  ohne Buchungen das gewählte Verfahren. Spanne aus den Fehlern des Rückwärtstests (10.–90. Perzentil). Eigene geplante
  Plätze ersetzen die Schätzung der Welle.
* **Für den Wirtschaftsplan:** Tabelle je Maßnahme mit Ø je Jahr, letzten 12 Monaten, Trend und den kommenden Wellen
  (erwartet mit Spanne), Summenzeile; Kennzahl „Erwartet <nächstes Jahr>“.
* **Ausgeblendet:** Maßnahmen ohne Start seit 24 Monaten (eingestellt) und Kleinstmaßnahmen (unter 5 Neuanmeldungen
  in 24 Monaten). Je Zeile von Hand ausblenden, unter „Ausgeblendete Maßnahmen“ wieder „immer zeigen“.

## Maßnahmen-Prognose ehrlicher, Abtipp-Modus (neu in 0.55)

* **Verbleib:** Gebuchte Kurse stehen im Pivot bis zum geplanten Ende voll drin. Jetzt werden sie mit der
  Verbleibskurve früherer Kurse derselben Art fortgeschrieben (Abbrüche, Wechsel zu „Pendler“). Bedingt: Wer schon
  lange dabei ist, bleibt eher. Neue Kurse aus den Vorjahren bringen ihren echten Verlauf mit – dort wird die Kurve
  nicht noch einmal angewendet (sonst doppelt gezählt). Gezeigt wird der Pivot-Wert höchstens bis Bestand × Verbleib.
* **Buchungsloch geschlossen:** Ist ein Kurs schon teilweise gebucht, entfiel bisher die Schätzung. Jetzt kommt die
  erwartete Nachbuchung dazu (Poisson-Gamma: gebucht + (1 − p) · (κ·Vorjahre + gebucht) / (κ + p), κ = 1,5). Weit vor
  Start zählen die Vorjahre, kurz vor Start der Buchungsstand; nie mehr als der größte Kurs der Vorjahre. Die
  Buchungskurve p(d) wird aus den Anreiselisten gemessen (wann stand jemand zuerst drin?), ab 30 Anreisen – vorher gilt
  die angezeigte Annahme „21 Tage vor Start ist die Hälfte gebucht“.
* **Kurzkurse** (Arten mit Kursen unter 45 Tagen): Saisonsockel je Kalendermonat aus den Vorjahren statt Einzelkurse
  im ±45-Tage-Raster (dort fielen bisher zwei von drei Kursen durch).
* **Rückwärtstest ohne Blick in die Zukunft:** laufende Kurse mit dem Bestand am Stichtag und der damals bekannten
  Verbleibskurve, alle späteren Kurse geschätzt, als wäre keiner gebucht (eher strenger). Daneben zum Vergleich ohne
  Verbleib – so sieht man an den eigenen Daten, ob die Kurve hilft. Unter dem Test steht, wie gerechnet wird.
* **Abtipp-Modus** (Anreisen → Firmenprogramm): ein Eintrag groß, je Feld ein Kopierknopf (TN-ID, Name, Zimmer,
  von, bis, Maßnahme), „Eingetragen – nächster“, Überspringen. Im eigenen Fenster per Knopf ein schmaler Streifen am
  rechten Rand, der im Vordergrund bleibt – daneben das Belegungssystem.
* **Schreibsperre mit Herzschlag:** Der PC, der speichert, erneuert die Sperre alle 10 s; eine Sperre ohne Herzschlag
  (PC abgestürzt) gilt nach 45 s als verwaist – lange Schritte (großer Import) verlieren ihre Sperre trotzdem nie.
* **Schrift:** Fließtext in Segoe UI (statt Candara), Überschriften und Kennzahlen weiter Bahnschrift; Ziffern in
  Tabellen gleich breit.

## Gemeinsamer Netzwerkordner für 7–8 PCs (neu in 0.54)

Ein Paket, das man nur entpackt – und alle PCs arbeiten auf denselben Daten.

* **Aufbau:** `INNternat starten.bat` · `LIESMICH.txt` · `Programm\` (wird bei einem Update ersetzt) · `Daten\`
  (gemeinsame Daten aller PCs, entsteht beim ersten Start und bleibt bei Updates unangetastet). Gebaut wird das Paket
  mit `python3 modern_ui/netz/paket_bauen.py INNternat.zip` – nur Dateien aus dem Repository, nie lokale Daten.
* **Jeder PC startet selbst.** Die Startdatei legt die Python-Umgebung lokal an (`%LOCALAPPDATA%\INNternat\venv`, einmal
  je PC), ebenso Protokoll, Zwischenspeicher (`.pyc`) und NiceGUI-Ablage – nichts davon im Netzwerkordner. Beim ersten
  Start kommt eine Verknüpfung „INNternat“ auf den Desktop. „Mit Windows starten“ läuft über die Startdatei.
* **Daten übernehmen:** Ist `Daten` noch leer, fragt INNternat nach dem bisherigen Ordner. *Prüfen* zeigt, was kopiert
  wird (Planung, Listen, Gebäudeplan, Vorlagen, Logo, Sicherungen, alle Standorte – keine Programmdateien), *Übernehmen*
  kopiert. Der bisherige Ordner bleibt unverändert und ist damit zugleich die Sicherung. Der gespeicherte Pfad zur
  Pivot-Datei wird auf die Kopie umgestellt. Übernommen wird nur in einen leeren Datenordner. Auch unter
  *Einstellungen → Sicherung & Verlauf*.
* **Schreibsperre:** Jede Änderung läuft unter einer kurzen Sperre im Datenordner (`.innternat_sperre`). Zwei PCs
  speichern nie gleichzeitig; wer gerade dran ist, wird kurz abgewartet (bis 15 s), sonst kommt „Gerade speichert …“.
  Eine Sperre eines abgestürzten PCs gilt nach 45 s als verwaist (seit 0.55 mit Herzschlag).
* **Speichern mit Wiederholung:** Liest ein anderer PC eine Datei gerade, verweigert Windows das Ersetzen – es wird
  einige Sekunden wiederholt. Bleibt eine Datei beim Lesen gesperrt, gibt es eine Meldung statt still mit leeren
  Daten weiterzurechnen (und sie danach zu überschreiben).
* **Wer hat geändert:** Die anderen PCs laden innerhalb von 30 s neu und zeigen kurz „Aktualisiert: … – gespeichert
  von Name an PC um 14:32“. Rückgängig nimmt weiterhin nur die eigene letzte Änderung zurück – und nur, solange danach
  niemand anderes an derselben Planung gespeichert hat.
* **Persönlich je PC:** Darstellung, „Später“, Begrüßung und der zuletzt gewählte Standort liegen lokal
  (`einstellungen_lokal.json`); beim ersten Start wird die bisherige gemeinsame Einstellung übernommen.
* **Tägliche Sicherung:** Beim ersten Start des Tages (und bei einer neuen Version) sichert genau ein PC die Daten
  jedes Standorts (30 Stände). Bisher übernahm das nur das alte Programm – ohne es gab es keine automatische Sicherung.
* **Update:** alle PCs schließen, `Programm` löschen, neues Zip entpacken. Ein PC, der noch läuft, meldet „Neue
  Version ist eingespielt – bitte neu starten“. Pivot-Dateien legt INNternat jetzt im Datenordner ab, nicht mehr im
  Programmordner.
* **Kleinigkeit aus dem Prüfbericht:** Zahlen auf *Heute* ohne führende Null („0“ statt „00“, „1“ statt „01“).
* **Bisheriges Programm (PySide):** läuft im Netzwerkordner nicht mehr. Es kennt weder Standorte noch Schreibsperre und
  würde neben den anderen PCs Daten überschreiben. Sein Code liegt als Bibliothek unter `Programm\belegung`; Startdatei
  und Oberfläche des alten Programms sind nicht im Paket.

## Maßnahmen im Vergleich, Zimmer hinzufügen (neu in 0.53)

**Auswertung → Maßnahmen** zeigt jetzt die Maßnahmen gegeneinander, nicht die Internatsbelegung (die steht in der
allgemeinen Prognose):
* Je Maßnahmenart eine eigene Kurve der **Teilnehmenden** (alle, nicht nur Internat): Ist durchgezogen, Prognose
  gestrichelt. Keine Summe, keine Betten, keine Kapazität.
* **Auswahl** (leer = alle mit Teilnehmenden im letzten Jahr, „Nur Hauptmaßnahmen“) und Schalter **Ein Diagramm |
  Je Maßnahme**. Bis 5 Maßnahmen startet das gemeinsame Diagramm, ab 6 das Raster mit einem kleinen Diagramm je
  Maßnahme (gleiche oder eigene Skala).
* Kennzahlen: am stärksten gewachsen bzw. geschrumpft, höchster bzw. niedrigster Verbleib. Darunter die
  Vergleichstabelle (ohne Internat), die Gruppe je Art ist dort änderbar.

**Zimmer hinzufügen und entfernen**:
* **Einstellungen → Zimmer-Stammdaten → „Zimmer hinzufügen …“** (auch Zimmer → Liste → Bearbeiten): Haus,
  Zimmernummer, Etage (wird aus der Nummer vorgeschlagen), Betten. Die Kennung entspricht der des Gebäudeplans, damit
  Buchungen später passen. Merkmale danach wie gewohnt in den Stammdaten.
* **Entfernen** im Stammdaten-Fenster: selbst angelegte Zimmer werden gelöscht (nur ohne laufende oder künftige
  Planung). Zimmer aus dem Gebäudeplan werden auf „gehört nicht zum Internat“ gesetzt; zurück über denselben Schalter.
* Rückgängig wie immer. Hinweis: Das bisherige Programm kennt die zusätzlichen Zimmer nicht.

## Maßnahmen auswählen und vergleichen (neu in 0.52)

* **Auswahlfeld „Maßnahmen“** oben in Auswertung → Maßnahmen: eine oder mehrere Arten wählen (mit Suche; leer =
  alle). „Alle Hauptmaßnahmen“ wählt sie mit einem Klick. Prognose, Kennzahlen und Tabellen gelten dann nur für die
  Auswahl.
* Ab zwei Arten: Umschalter **Summe | Vergleich**. Im Vergleich hat jede Maßnahme eine eigene Linie (Ist
  durchgezogen, Prognose gestrichelt).
* **Maßnahmen im Vergleich** (Tabelle, ohne Auswahl für alle Hauptmaßnahmen, Vorbereitung und IBTZ):
  Teilnehmertage der letzten 12 Monate, **Trend zum Vorjahr** (grün ab +10 %, rot ab −10 %), Kursstarts je Jahr,
  **Kursgröße jetzt und in den drei Jahren davor**, Verbleib bis Kursende (rot unter 60 %), Internatsanteil, heute
  und in 12 bzw. 24 Monaten.
* Für die Frage, ob sich eine Maßnahme lohnt, zeigt das die Nachfrage-Seite. Für eine Wirtschaftlichkeit fehlen
  Erlöse und Kosten je Maßnahme.

## Maßnahmen-Prognose übersichtlicher (neu in 0.51)

* **Standard ist die Belegung im Internat (Betten).** Eine Linie: **durchgezogen = Ist**, ab heute **gestrichelt =
  Prognose**; der Prognosezeitraum ist hell hinterlegt. Dazu das **Band** der Spanne, **„sicher gebucht“**
  (gepunktet – was laut Pivot schon feststeht) und die **Kapazität** (rot, aus dem Standort-Pivot).
* Zeitraum **12, 24 oder 36 Monate**.
* Kennzahlen: heute im Internat und die Prognose in 6, 12 Monaten und am Ende des Zeitraums – je mit Spanne, sicher
  gebucht und Anteil an der Kapazität (orange ab 90 %, rot ab 100 % der oberen Spanne).
* Die Aufteilung nach Maßnahmengruppen steht darunter zum Aufklappen.
* Erwartete neue Kurse aus **bis zu drei Vorjahren** (Mittel, Spanne = kleinstes/größtes Jahr). Kam ein Kurs nur in
  einem Teil der Jahre vor, zählt er anteilig.
* **Einlesen mit Bestätigung**: Beim Hochladen erscheint ein Fenster „wird eingelesen“, danach die Zusammenfassung
  (Kurse, Zeitraum, überbrückte Tage bzw. Kurse und Pendler-Anteil) mit Knopf zur Maßnahmen-Prognose.

## Maßnahmen-Prognose (neu in 0.50)

**Einlesen** – Daten & Import → „Maßnahmen-Prognose“:
* **Maßnahmen-Pivot** (Personen mit ihren Maßnahmen je Tag, z. B. `pivot_TNHM.xlsx`). Übernommen werden nur die
  Maßnahme-Zeilen als Teilnehmerzahl je Kurs und Tag – **keine Namen**; die hochgeladene Datei wird danach gelöscht.
  Fehlende Tage (z. B. ein Monat, der im Pivot zugeklappt war) werden je Kurs mit dem letzten Wert überbrückt und
  angezeigt. Ein großer Pivot braucht ein paar Minuten.
* **Anreiselisten „Teilnehmer Beginn“ als Word oder PDF**: Je Kurs nur Teilnehmende, Pendler und Kostenzusagen.
  **P = Pendler, ohne P = Internat, K = Kostenzusage.** Daraus kommt der Internatsanteil je Maßnahmenart.

**Ansehen** – Auswertung → **Maßnahmen** (eigener Reiter, die bisherige Prognose bleibt unverändert):
* Umschalter **Teilnehmende | Internat (Betten)** und 12/24 Monate (ab 0.51: 36 Monate, Standard Internat).
* Fläche je Gruppe: **Hauptmaßnahmen** (Teilnahme ≥ 300 Tage), **RVL/RVT**, **IBTZ**, **übrige** (Assessment, EMR,
  Info …); „ohne Zimmer“ (z. B. virtueller Infotag) fällt heraus. Die Summe passt immer zur Gesamtzahl.
* **Prognose = gebuchter Bestand + erwartete neue Kurse.** Jede Art startet im festen Rhythmus; für jeden Kurs der
  letzten zwei Jahre wird derselbe Kurs ein Jahr später angenommen (Mittel beider Jahre, Spanne = kleineres/größeres
  Jahr). Schon gebuchte Kurse zählen nicht doppelt.
* **Geplante Plätze …**: z. B. „GS VW, 2027-06, 22 Plätze“ ersetzt die Schätzung für diesen Start – der größte Hebel
  für das zweite Halbjahr.
* Tabelle je Hauptmaßnahme: heute, in 6 und 12 Monaten, nächster Start (gebucht/erwartet/geplant), übliche
  Kursgröße, Verbleib bis Kursende, Internatsanteil; die **Gruppe** ist je Art änderbar.
* **Rückwärtstest**: Wie weit hätte die Prognose je Jahr (Stichtag 1. Januar) daneben gelegen – getrennt nach
  erstem und zweitem Halbjahr.
* **Abgleich mit dem Standort-Pivot**: je Monat Teilnehmende laut Maßnahmen-Pivot gegen die Belegung laut
  Standort-Pivot – nahe 100 % heißt, beide zählen dasselbe.

**Korrektur**: Der PDF-Import für Bad Pyrmont und Weser-Ems las bisher „K = Internat“. Richtig ist **P = Pendler**,
ohne P Internat; K ist die Kostenzusage. Listen, die schon eingelesen sind, bitte einmal neu einlesen.

## Archiv früherer Anreisen (neu in 0.49)

* **Anreisen → Mehr → „Archiv: frühere Anreisen suchen …“**: Zeitraum wählen (beliebig weit zurück, Standard die
  letzten 90 Tage), optional nach Name, Maßnahme, Gruppe oder Zimmer filtern.
* Je Person: Anreise (laut Liste), Gruppe, Maßnahme, Zeitraum und **Zimmer** – laut eigener Planung, sonst laut
  Gebäudeplan (gleicher Name, Zeitraum überlappt), sonst laut Zimmerhistorie. Die Spalte „laut“ sagt, woher.
* **Drucken** (nach Anreisetagen gegliedert) und **Excel** (alle Treffer).
* Grundlage: Es gibt nur Anreisen, deren Liste in INNternat eingelesen wurde; gelöscht wird nichts automatisch.
* Die normale Auswahl bleibt schlank: ab 3 Tagen zurück, über „Auch vergangene Anreisen zeigen“ 12 Monate.

## Budget je Topf und Haushaltsjahr (neu in 0.48)

Steuerung → **Finanzen** rechnet jetzt wie der Haushalt:

* **Haushaltsjahr = Kalenderjahr.** Je Topf (Bau, Möbel/Einrichtung, sonstiges) und Jahr: **Budget · verbraucht ·
  geplant offen · Vorschlag · frei**, dazu gebunden (Aufträge), abgerechnet (Rechnungen) und bezahlt.
* **Verbraucht beim Auftrag** (Standard, je Topf umstellbar auf „bei Rechnung“ oder „bei Zahlung“): Ein Auftrag im
  Dezember verbraucht das Budget des Auftragsjahres – die Schlussrechnung im Januar belastet das neue Jahr nicht, sie
  erscheint dort nur unter abgerechnet/bezahlt. Gezeigt werden Planjahr und Folgejahr.
* **Frei** = Budget − verbraucht − geplant offen − Renovierungsvorschlag. Der Renovierungsvorschlag verteilt nur, was
  danach frei ist. Abgelehnte Vorhaben zählen nicht. Klick auf einen Topf zeigt alle Positionen.
* **Budget je Jahr & Regeln …**: Budget je Topf und Jahr (leer = Bau aus der Vorgabe), die Regel je Topf und wer
  freigibt (Standard „Leitung“, eine Stufe). Beim Freigeben eines Vorhabens werden Wer und Datum eingetragen, wenn sie
  fehlen. In der Entscheidungsvorlage heißt es „Beschluss (Leitung)“.
* **Angebote** gelten ohne Angabe bis zum 31.12. des Angebotsjahres – bis dahin keine Preissteigerung.

## Vorhaben – Maßnahmen – Kostenpositionen (neu in 0.47)

Steuerung → **Vorhaben** ist jetzt das Portfolio aller Vorhaben, nicht nur der Renovierung.

* **Neues Vorhaben …**: Titel, Kategorie (Renovierung, Möbel, Technik, Brandschutz, Außenanlage, IT, Sonstiges), Haus,
  Priorität.
* **Haupttreiber – genau einer**: Pflicht, Risiko, Wirtschaftlichkeit, Kapazität, Qualität. **Pflicht** speichert nur
  mit Nachweis (Rechtsgrundlage, Vorgabe oder Prüfprotokoll), die anderen mit einer kurzen Begründung. Pflicht-Vorhaben
  stehen oben in der Liste.
* **Drei Statusachsen**:
  * **Entscheidung** von Hand: Idee · in Prüfung · beantragt · freigegeben · abgelehnt, mit Datum und Wer.
  * **Umsetzung** ergibt sich selbst: offen · terminiert (Maßnahme mit Termin) · beauftragt (Auftrag erfasst) · in Arbeit
    · abgeschlossen.
  * **Finanzen** ergeben sich selbst: geschätzt · gebunden (Auftrag) · teilweise bezahlt · abgerechnet.
  * Widersprüche (z. B. „Idee, aber schon beauftragt“, abgelaufenes Angebot) stehen am Vorhaben und im Cockpit.
* **Maßnahmen** mit von/bis und **Kostenpositionen** mit Betrag, Herkunft, Haushaltsjahr, Topf (Bau/Möbel/sonstiges),
  „gültig bis“, Bemerkung, **Auftrag** (Betrag, Datum) und **Rechnungen** (Betrag, Datum, bezahlt am).
* **Renovierung als Vorhaben**: Die Vormerkungen aus „Renovierung planen“ erscheinen automatisch als
  „Renovierung <Jahr>“ – Maßnahmen und Beträge kommen weiter aus der Planung (nichts doppelt). Ergänzt werden Treiber,
  Entscheidung, Aufträge und Rechnungen.
* **Andere Vorhaben verbrauchen ihren Topf**: Eine Bau-Position 2027 eines anderen Vorhabens zählt im Cockpit
  („Bau verplant/frei“), unter Finanzen (Spalte „Weitere Vorhaben“) und im Renovierungsvorschlag (verteilt nur den
  Rest). Abgelehnte Vorhaben zählen nicht.
* Unter **Zeitplan & Kapazität** stehen die Termine der weiteren Vorhaben.
* Gespeichert in `importe/modern_vorhaben.json` (mit gesichert), Rückgängig wie immer.

## Steuerung nach Fragen gegliedert, Leiste wie in Office, Showcase-Dock (neu in 0.46)

* **Steuerung in fünf Bereichen** – nach Fragen statt nach Werkzeugen:
  * **Cockpit** (nur lesen): höchstens 5 Kennzahlen, 3 Warnungen, 3 Handlungsempfehlungen. Jede Kachel führt per Klick
    zur passenden Ansicht.
  * **Vorhaben**: oben die Liste des Vorgemerkten, darunter das Werkzeug „Renovierung planen“ in drei sichtbar
    getrennten Zonen: **1 Eingabe** (Vorgabe, eigene Etage) · **2 Ergebnis** (Empfehlung, Varianten, Zeitplan, Etagen)
    · **3 Entscheidung** (was offen ist, „Alle Vorschläge übernehmen“).
  * **Zeitplan & Kapazität**: Gantt, Belegung mit Prognose und Kapazität minus Baustellen, Prognosegüte, Kernbestand.
  * **Finanzen**: Budget je Topf (Bau, Möbel) mit vorgemerkt / Vorschlag / frei, darunter die Strategie über 5 Jahre.
    Planungshorizont überall sichtbar (auch im PDF): Jahr 1 belastbar, Jahr 2 wahrscheinlich, Jahre 3–5 Orientierung.
  * **Grundlagen**: Annahmen mit Herkunft, Angebote mit Datum und Gültigkeit, Kennzahlen und Datenlücken.
* **Festpreis**: Beim Angebot „gültig bis“ eintragen (wird im PDF erkannt). So lange rechnet INNternat keine
  Preissteigerung darauf, erst ab dem Jahr nach Ablauf.
* **Nie nur zum Ausschöpfen**: Bei gleichem Bedarf gewinnt die günstigere Lösung, Etagen ohne erfassten Bedarf zählen
  nicht. Restbudget bleibt sichtbar frei – „verfällt am 31.12.“.
* **Eine Tabellenvorlage**: Kopfzeile und Zeilen teilen ein Spaltenraster – die Kopfzeile steht immer über den Werten.
* **Seitenleiste wie in Office** (Layout Enterprise Grid): „Leiste einklappen“ → nur Symbole; beim Darüberfahren klappt
  sie nach kurzer Verzögerung über dem Inhalt auf (nichts verschiebt sich). „Leiste anheften“ hält sie offen (Strg+B).
* **Showcase-Dock** mit allen Bereichen: angeheftete Bereiche direkt im Dock, der Rest je Gruppe (Betrieb, Überblick,
  Verwalten, Leitung) als Menü; rechts Suche, hell/dunkel, Anheften und **Dock anpassen** (welche Bereiche im Dock
  stehen). Nicht angeheftet blendet sich das Dock aus und fährt beim Darüberfahren herein (Strg+B).
* **Gästezimmer nicht in der Auslastung**: Sie stehen weiter in den Häusern und Listen, zählen aber nicht in die
  prozentuale Auslastung der Zimmerliste (Hinweis „ohne … Gästezimmer“).

## Ganze Etage selbst planen (neu in 0.45)

Steuerung → Renovierung → **„Ganze Etage selbst planen“**: Etage wählen (mit Zimmerzahl und Bau laut Angebot) →
**„Monat wählen und vormerken …“** zeigt Kosten (Bau laut Angebot, Bau im Planjahr, Möbel), den besten Monat zum
direkten Vormerken und alle Monate zum Auswählen. Gilt auch für Etagen, für die (noch) kein Bedarf erfasst ist und die
INNternat deshalb nicht von sich aus vorschlägt. Klick auf eine Zeile in „Bedarf und Kosten je Etage“ öffnet dasselbe.

Was vorgemerkt ist, **verbraucht Baubudget bzw. Zimmerziel**: Der Vorschlag darunter verteilt nur noch den Rest, und
der Möbelantrag, die Kennzahl „Bau verplant“ und die Entscheidungsvorlage zählen die Vormerkung mit. Passt eine Etage
nicht mehr ins freie Baubudget, sagt INNternat das vorher – vormerken geht trotzdem („überschritten um …“).

## Steuerung überarbeitet: Klassen, Baubudget fest, Möbelantrag, Kernbestand (neu in 0.44)

**0.44.1 – Angebot einlesen erkennt die Summe:** In PDFs stehen zwischen „Nettosumme“ bzw. „Warenwert o. MwSt.“ und dem
Betrag oft Dutzende Leerzeichen – das wurde nicht erkannt (Summe 0 €). Jetzt werden Nettosumme, Haus, Positionen und
Einheitspreise gelesen; fehlt die Summe trotzdem, sagt das Prüf-Panel es deutlich. Ein Möbel-Angebot lässt sich
**„für alle Häuser“** übernehmen. Der geschätzte Einzelzimmer-Preis in den Annahmen rechnet mit der typischen
Zimmerzahl der Etage des Hauses.

**Beträge, die man wiedererkennt.** Die Bau-Spalte zeigt den Preis **so, wie er im Angebot steht** (inkl. nicht
abziehbarer Steuer) – daneben getrennt „Bau im Planjahr“ (mit Preissteigerung) und Möbel. Jede Zahl trägt ihre
Herkunft: *Angebot*, *Eingabe*, *Schätzung* oder *Platzhalter*. Hat ein Haus noch kein eingelesenes Angebot, steht oben
ein deutlicher Hinweis („Haus 2: kein Bau-Angebot – Platzhalter 100.000 € netto je Etage“) mit Knopf zum Einlesen.
Puffer gibt es je Budget (Bau/Möbel) und sie stehen standardmäßig auf **0 %** – sonst gilt der Angebotspreis.
Beträge auf 1.000 € gerundet, mit Spanne (Angebot ±10 %, Eingabe ±15 %, Schätzung ±25 %, Platzhalter ±40 %).

**Bedarf in Klassen statt Punkten**, getrennt für Bau und Möbel: **A** = jetzt (Renovierung nötig, Schimmel, Note 5,
≥ 20 Jahre; Möbel/Matratze defekt), **B** = in 1–3 Jahren (Note 4, ≥ 15 Jahre, Boden/Wand), **C** = später.
In den letzten 5 Jahren renoviert = kein Bau (Möbel gehen). Erst alle A, dann B, dann C.

**Baubudget fest, Möbel als Antrag.** Das Baubudget ist die Grenze, die verfällt – INNternat verplant es möglichst voll
in gedeckten Bedarf; ein Rest steht als Hinweis da. Den Möbelbedarf rechnet INNternat aus (für die Bau-Maßnahmen +
„nur Möbel“ für Zimmer mit dringendem Möbelbedarf) – das ist der Antrag; eine realistische Obergrenze ist optional.
Baubudget ist jetzt die Standard-Vorgabe; Zimmerziel bleibt wählbar. Dazu „Reihenfolge: Haus 2/6 zuerst“.

**Beste Kombination.** Jede Etagenkombination im Baubudget wird mit Einzelzimmern nach Bedarf je € aufgefüllt; die
beste Gesamtlösung gewinnt („Rechnerisch beste Variante unter den Annahmen“). Etagen ohne Bedarf oder ohne machbaren
Monat fallen vorher heraus. Ein Satz zeigt, ob die Empfehlung bei Kosten ±15 % stabil bleibt.

**Einzelzimmer mit Einheitspreisen.** Beim Einlesen eines Bau-Angebots liest INNternat die Positionen und errechnet
€/m² Boden, €/m² Wand+Decke und € je Tür. Mit den Zimmerflächen (unter Annahmen je Haus) wird ein Einzelzimmer daraus
gerechnet; ohne Flächen bleibt es eine gekennzeichnete Schätzung.

**Termine.** Hinter den bekannten Buchungen heißt ein Monat „nicht prüfbar“ (grau) statt grün. Zeichen im Plan:
⚑ = Ausweichzimmer fehlt, ▲ = Warnschwelle. Einzelzimmer werden in höchstens zwei **Kampagnen** je Haus gebündelt,
frühestens nach Bestellung + Möbel-Lieferzeit (Standard 4 Wochen). Bauzeit einer Etage: 1 Monat (Haus 2 und 6).

**Kernbestand und Reserve.** Kern = Spitzenbedarf (obere Prognose) + Ausfallreserve + Typen-Reserve + Puffer; der Rest
ist Reserve. INNternat schlägt **ganze** Reserve-Etagen vor (teuerste je Zimmer, keine EMR-/Gäste-/Kurzmaßnahmen-
Etagen) und zeigt, wie viele Betten bei +10 % Nachfrage fehlen würden. Mit dem Häkchen „Reserve-Etagen nicht
renovieren“ fallen sie aus der Planung – die Entscheidung trifft die Geschäftsführung.

**Strategie 5 Jahre** mit Alterung: Nichtstun · Empfohlen · Kürzung −20 % · Beschleunigt +50 % · Kernbestand – je mit
offenen A-Zimmern heute → am Ende, Zimmer, Bau, Möbel, Zyklus.

**Entscheidungsvorlage:** Seite 1 = Kurzfassung (Beschlussvorschlag, Beträge je Kostenstelle mit Spanne, Maßnahmen,
Warum, Wenn nicht, Wenn −20 %, Risiken, nächste Schritte mit Datum und Frist, Beschlussfeld für Bau und Möbel),
danach Anhang A–H mit allen Erläuterungen. Ansichten heißen jetzt Übersicht · Renovierung · Strategie 5 Jahre ·
Belegung · Kennzahlen; Varianten, Bedarf je Etage und Annahmen sind eingeklappt.

## Einzelzimmer, Wege im Vergleich, Entscheidungsvorlage (neu in 0.43)

**Renovierung – nicht nur ganze Etagen.** Drei Arten von Maßnahmen:
* **ganze Etage** (wie die Angebote gelten),
* **Einzelzimmer komplett** – Maler/Boden anteilig aus dem Etagenangebot + Aufschlag (Standard 25 %, kleiner Auftrag),
  oder ein eigener Preis je Haus („Bau je Einzelzimmer“ unter Annahmen),
* **nur Möbel tauschen** – nur Möbel + Aufbau, braucht nur das Möbelbudget und wenige Tage Leerstand.

**Wege im Vergleich** (für Zimmerziel und Budget): *Nur ganze Etagen* · *Etagen + Einzelzimmer* (der Rest geht in die
bedürftigsten Zimmer) · *Nur Einzelzimmer* · *Nur Möbel*. Je Weg: Zimmer, gedeckter Bedarf, Bau, Möbel, Rest der
Budgets, Sperr-Zimmermonate. **★ Empfehlung** = meister gedeckter Bedarf, dann mehr Zimmer, dann günstiger; „nur
Möbel“ zählt halb, weil Wände und Böden bleiben. Klick wählt einen anderen Weg. Einzelzimmer kommen in den ersten
Leerstand im Jahr, der lang genug ist (Einzelzimmer 14, Möbel 3 Tage – änderbar).

**Kosten nachvollziehbar.** Im Jahresplan steht je Maßnahme Gesamt, Bau und Möbel; Klick zeigt die Herleitung Schritt
für Schritt: Angebot/Annahme Bau → Preissteigerung → Nebenkosten → Möbel → Aufbau → Puffer → Umsatzsteuer. Darum
liegt eine Etage über dem reinen Maler-/Bodenangebot. Solange kein Angebot eingelesen ist, rechnet INNternat mit der
Platzhalter-Annahme (Haus 2: 100.000 € netto je Etage).

**Szenarien über 5 Jahre:** wie eingestellt (jedes Jahr die empfohlene Variante), 1 bzw. 2 Etagen je Jahr, nur Möbel,
ein Jahr warten. Je Strategie: Zimmer, Anteil am Bestand, Kosten, je Zimmer, Zyklus, Sperr-Zimmermonate, Jahr-für-Jahr
und ein Satz „was heißt das“; dazu Kosten und Zimmer kumuliert als Diagramm.

**Kennzahlen – Werte eingeben …:** Tagessätze je Gruppe (→ Erlös 12 Monate, Ø je Belegtag, Leerstandskosten),
Abweisungen „kein Zimmer frei“ je Monat, **Zustandsnote je Etage** (1–5, fließt in den Bedarf: 4 → +2, 5 → +4 je
Zimmer). Zum Ausprobieren gehen erfundene Zahlen; Rückgängig wie immer.

**Entscheidungsvorlage (PDF)** statt Kurzbericht: Worum es geht, Empfehlung mit Beschlussfeld, Varianten, Zeitplan,
Herleitung der Kosten, Belegung und Kapazität, Szenarien, Kennzahlen, Annahmen, Begriffe – jeder Abschnitt mit „So zu
lesen“. Ist bewusst ein anderer Weg gewählt, steht das dabei.

Die Kopfleiste der Steuerung hat keinen Hinweistext mehr. **Auswertung → Zimmer & Engpässe:** Klick auf die EMR- oder
Doppelzimmer-Zahl bzw. auf „knapp – EMR“ zeigt die Woche im Detail: freie Zimmer je Tag, welche Zimmer ganz/teilweise
frei sind und wer wann drin ist (probeweise zugeteilte Anreisen markiert).

## Renovierung nach Budget – Bau und Möbel getrennt (neu in 0.42)

Steuerung → Renovierung → **Planen nach: Zimmerziel | Budget**. Bau und Möbel laufen über **zwei verschiedene
Kostenstellen**, deshalb gibt es zwei Budgets je Jahr:

* **Budget Bau** – Maler/Boden und Nebenkosten (Instandhaltung),
* **Budget Möbel** – Möbel und Aufbau.

Ein leeres Feld heißt „keine Grenze“. Beträge so, wie sie bei euch zählen (mit Puffer und nicht abziehbarer
Umsatzsteuer laut Vorsteuerquote). INNternat sucht dann selbst:

1. **Welche Etagen:** die Kombination ganzer Etagen mit dem meisten Bedarf, die in **beide** Budgets passt (bei
   gleichem Bedarf die mit den meisten Zimmern, dann die günstigere). Passt keine, nennt es die günstigste Etage.
2. **Wann:** je Etage den Monat mit den wenigsten Engpässen – zuerst: alle Betroffenen haben ein Ausweichzimmer;
   dann: die obere Prognose bleibt unter der Warnschwelle der Kapazität **minus dieser und schon geplanter
   Baustellen**; dann: möglichst wenige Umzüge und Mieter. Zwei Etagen kommen nie in denselben Monat.

Angezeigt werden verplant und Rest je Budget (auch in der Übersicht und unter „Zu entscheiden“). Ein Monat an der
Warnschwelle ist orange – wenn es trotzdem dieser wurde, gab es keinen besseren. Übernommen wird wie bisher erst nach
Bestätigung.

## Steuerung für die Leitung (neu in 0.41)

Für die strategische Planung – selten gebraucht, deshalb **ein einziger Eintrag ganz unten in der Seitenleiste**
(Gruppe „Leitung“). Die Seite rechnet erst, wenn sie geöffnet wird; Start und Tagesbetrieb merken davon nichts.
Sie gilt für Goslar (Prognose, Haus 2 und 6). Die Gruppe „Täglich“ heißt jetzt „Betrieb“.

* **Übersicht** (5 Minuten): vier Kennzahlen (höchste Belegung, Monate an der Warnschwelle, Renovierung geplant/Ziel,
  Kosten mit Bau/Möbel getrennt), ein Diagramm mit Ist, Prognose samt Spanne, **Vorjahr** und der **Kapazität minus
  Baustellen** (knickt ein, wenn eine Etage gesperrt ist), der Jahresplan, die Szenarien und „Zu entscheiden“.
  **Bericht drucken / PDF** gibt das als eine Querformat-Seite aus.
* **Renovierung** (bisher unter Zimmer):
  * **Zimmerziel statt Budget:** „9 Zimmer je Jahr“ ≙ „jedes Zimmer etwa alle N Jahre“. Weil die Angebote je Etage
    gelten, werden ganze Etagen nach Bedarf gewählt; geht das Ziel nicht auf, stehen zwei Vorschläge da (knapp
    darunter, knapp darüber) – mit Kosten. Vorausgewählt ist der, der näher am Ziel liegt.
  * **Kosten aus Angeboten:** je Haus Bau (Maler/Boden) je Etage, Möbel und Aufbau je Zimmer, Bauzeit; dazu
    Nebenkosten % (Elektro, Sanitär …), Puffer %, Preissteigerung je Jahr ab Preisstand und eine **Vorsteuerquote**
    (0 % = Umsatzsteuer ist Kosten, also brutto; mit der Buchhaltung klären). Ausgewiesen getrennt:
    Bau + Nebenkosten (Instandhaltung) und Möbel + Aufbau (Investition). **„Angebot einlesen (PDF)“** liest die
    Nettosumme, erkennt Bau oder Möbel, Haus und bei Möbeln die Zimmerzahl – zur Prüfung, gespeichert wird erst nach
    „Übernehmen“ und nur der Betrag (im Datenordner, nie im Programm). Fehlende Preise stehen als Lücke da.
  * **Jahresplan als Gantt:** Zeilen = Etagen, schraffiert = Belegungsstopp, Balken = Bauzeit; **Vorschläge
    gestrichelt**, vorgemerkte ausgefüllt. Klick → Kosten und „Bestätigen und vormerken“; „Alle Vorschläge
    übernehmen …“ zeigt die Liste und speichert nach Bestätigung (ein Rückgängig).
  * **Ausweichprüfung:** Für jede Person, die im Bauzeitraum im Flur wohnt oder anreist, wird ein passendes freies
    Zimmer in **allen** Häusern gesucht – wie beim Zuteilen (Gruppe, „nur Männer“, Gäste-, EMR-, Doppelzimmer).
    Fehlt eins, wird der Monat orange („eng“) und die Person steht in der Liste.
  * **Monatswahl ehrlich:** Sagen die Buchungen nichts (z. B. für das übernächste Jahr), hilft die Prognose – aber
    nur, wenn ihr Abstand größer ist als die halbe Spanne. Sonst heißen die Monate „gleichwertig“ (≈) und der früheste
    wird vorgeschlagen.
  * **Bedarf:** über 15 Jahre nicht renoviert (2 P.), „Renovierung nötig“ (4 P.), offene Mängel jetzt schwächer
    (0,5–1,5 P., sie messen auch das Reparaturtempo), in den letzten 5 Jahren renoviert (−3 P.); dazu Ø Jahre seit
    Renovierung. Gespeicherte Kostenannahmen von 0.39/0.40 (Flur-Pauschale) werden nicht übernommen – bitte die
    Angebote einlesen oder eintragen.
* **Szenarien:** 1 / 2 / 3 Etagen je Jahr – Zimmer, Kosten, Sperr-Zimmermonate, Jahre bis jede Etage dran war, Zyklus.
* **Prognose:** 12 Monate Ist, 24 Monate Prognose mit Vorjahr und Baustellen-Kapazität. **Güte ehrlich:** Die
  Rückblick-Monate werden geteilt – die älteren bestimmen die Spanne, die jüngsten 6 prüfen sie. Für die Leitung ein
  Satz: „lag im Schnitt um ±X Plätze daneben“. **Buchungsstände** werden ab jetzt einmal im Monat festgehalten
  (Grundlage für ein späteres Pickup-Modell). Die ausführliche Prognose bleibt unter Auswertung.
* **Kennzahlen** nur aus vorhandenen Daten: verfügbare Betten (ohne defekte und Baustellen), Auslastung darauf,
  Belegtage je Gruppe, Ausfalltage durch Defekte mit Ø Tagen bis bezugsfertig, Ø Jahre seit Renovierung, Zimmer
  innerhalb des Zyklus. Was neue Daten bräuchte (Erlöse, Abweisungen, Zustandsnote, Pickup), steht als Lücke da.
* **Engpässe** bleiben im Tagesbetrieb unter Auswertung → Zimmer & Engpässe.

## Haus 6 neu aufgeteilt, Flur = Etage (neu in 0.40)

* **0.40.1 – Ladezeiten behoben:**
  * Die Haus-6-Regel fragte bei jeder einzelnen Zimmerprüfung die Einstellungsdatei ab. Beim Zuteilen sind das
    hunderttausende Prüfungen, und jede wurde etwa 17-mal langsamer. Jetzt wird höchstens alle 2 Sekunden
    nachgesehen. Im Test mit 250 Personen braucht „Heute“ damit 2,7 statt 6,9 s, mit echten Daten ist der Gewinn
    größer.
  * Rechnet das Programm einmal länger, bleibt die Seite stehen, statt nach 3 Sekunden leer neu aufgebaut zu werden.
    Das war das „nur noch Hintergrund“.
  * „Bezugsfertig“ prüft die Tageszentrale nur noch für die nächsten 3 Tage.

* **Haus 6, Bad über den Flur:** Je Etage haben die Zimmer **x01, x02, x08 und x09** das Bad über den Flur und
  bleiben nur für Männer. Das Hauptprogramm führte zusätzlich x05 so; das ist in der neuen Oberfläche korrigiert.
  Eigene Angaben in den Zimmer-Stammdaten gehen weiter vor.
* **Haus 6: Aufteilung je Etage** (Einstellungen, schaltbar, mit Vorschau und Rückgängig):
  * **Hauptmaßnahmen** dürfen in die 5 Zimmer mit eigenem Bad. Das entlastet Haus 2.
  * Auf **renovierten Etagen** (alle Zimmer mit Renovierungsvermerk) bekommen **Mieter bevorzugt x01/x02** und
    **UWT bevorzugt x08/x09**. Die Zimmer mit eigenem Bad bleiben dort möglichst für Hauptmaßnahmen frei.
  * Nichts ist reserviert: Es gibt nur Vorrang bei der Zimmerwahl.
  * Vor dem Einschalten zeigt eine Vorschau, welche Vorschläge für Anreisen der nächsten 8 Wochen sich ändern
    würden.
  * **Achtung:** Das Hauptprogramm kennt diese Aufteilung nicht. Zuteilen dann nur in der neuen Oberfläche.
* **Renovierung:** Ein Flur ist die **ganze Etage**, in Haus 2 (Ost und West gehören baulich zusammen) und in Haus 6
  (9 Zimmer, ≈ 40.000 €). Mit 100.000 € passen 1 Etage in Haus 2 oder 2 Etagen in Haus 6.

## Ehrliche Prognose-Kennzahlen, Renovierungsplanung (neu in 0.39)

**Prognose (Auswertung → Prognose):**
* **Zeitraum durchgängig:** Kennzahlen, Szenario-Vergleich, Standortvergleich und die Executive-PDF folgen jetzt
  der Auswahl 12/24/36 Monate. Vorher blieben sie fest bei 12.
* **„Monate an der Warnschwelle“** statt „Kapazitätsrisiko“. Gezählt werden die Monate, deren obere 80 %-Grenze
  85 % der Kapazität erreicht. Das ist eine Schwellenprüfung, keine Wahrscheinlichkeit. Die Erklärung steht jetzt
  sichtbar unter jeder Kennzahl, nicht nur beim Darüberfahren.
* **Ab Monat 13 nur fortgeschrieben:** Der Backtest prüft bis 12 Monate. Danach ist die Prognose im Graph grau
  hinterlegt, in der Tabelle als „fortgeschrieben“ markiert und in der PDF mit ¹ gekennzeichnet.
* **Prognosegüte ohne grüne Ampel:** Das 80 %-Band wird aus denselben Rückblick-Fehlern bestimmt, die Trefferquote
  liegt deshalb fast zwangsläufig bei 80 %. Das steht jetzt dabei, statt als Gütesiegel grün zu leuchten.
* **Untere Bandgrenze nie unter dem gebuchten Bestand:** Was schon gebucht ist, steht fest.

**Zimmer → Renovierung** (unverbindliche Planung, nur Haus 2 und 6; nichts wird gesperrt oder umgezogen):
* **Welcher Flur als Nächstes?**
  * **Bedarf** in Punkten je Zimmer: Mängel nach Stufe (3/2/1), „Renovierung nötig“ (4 P.), länger als 90 Tage
    offen (+1 P.). Zimmer, die in den letzten 5 Jahren renoviert wurden, senken den Bedarf (−3 P.).
  * Jeder Grund steht dabei. Fehlende Renovierungsvermerke stehen als **Lücke** da, nicht geschätzt.
  * Dazu Sonderzimmer (EMR, Kurzmaßnahmen/Allergiker, Gäste, „nur Männer“), die Kosten laut Annahme und der
    beste Monat im gewählten Jahr.
* **Was passt ins Budget?** Je Haus die bedürftigsten Flure, solange die obere Kostenschätzung ins Jahresbudget
  passt.
* **Monate je Flur:**
  * Für jeden Monat steht da, wer im Bauzeitraum wohnt (Umzug nötig) oder anreist (umleiten), ab wann ein
    Belegungsstopp nötig ist, wie viele Zimmer im Haus frei sind und welche Mietverträge betroffen sind.
  * Grundlage sind nur bekannte Buchungen. Der beste Monat ist mit ★ markiert.
  * Ein Klick zeigt alle Einzelheiten. **„Vormerken“** speichert nur einen Plan-Eintrag (mit Rückgängig).
* **Jahresplan:** je Monat Flure, Zimmer und Betten, dazu die Jahressumme und die Kosten gegen das Budget. Export
  über **Excel**.
* **Annahmen** (änderbar):
  * Kosten Haus 2 = 100.000 € je Flur
  * Kosten Haus 6 = 10.000 € je Flur + 3.000–4.000 € je Zimmer
  * Budget 100.000 € je Jahr
  * Dauer 30 Tage
  * Belegungsstopp 56 Tage vorher
  * gesperrte Monate
  
  Gespeichert wird das in `importe/modern_renovierung.json`. Belegungsdaten werden dabei nicht verändert.

## Tageszentrale und Darstellung „INNternat“ (neu in 0.38)

* **Laptop (0.38.1):** Geprüft bei 1024, 1280 und 1536 px Fensterbreite, z. B. 1920×1080 mit 125–150 %
  Skalierung oder 1366×768.
  * Unter 1200 px Breite wird die Seitenleiste automatisch schmal: Symbole mit Tooltip, Zähler bleiben sichtbar.
  * Breite Tabellen scrollen waagerecht, statt Spalten abzuschneiden.
  * Die Tageszentrale rückt enger zusammen: Knöpfe unter dem Text, kleinere Kennzahlen, flacherer Kopf bei
    niedriger Fensterhöhe.
* **Neue Darstellung „INNternat“** (wird beim ersten Start einmalig eingeschaltet):
  * Layout mit dauerhaft sichtbarer, beschrifteter Seitenleiste. Einklappen mit Strg+B oder „Leiste einklappen“.
  * Türkis-Grau als Akzent. Überschriften und Kennzahlen in Bahnschrift, Text in Candara. Beides sind
    Windows-Schriften, sonst gelten die System-Schriften.
  * Hell und dunkel, umschaltbar direkt in der Seitenleiste („Helle/Dunkle Darstellung“). Die Wahl wird
    gespeichert.
  * Alle Texte und Statusfarben haben mindestens 4,5:1 Kontrast. Die Statusfarben (frei grün, belegt blau, Mangel
    orange, kritisch rot) sind bewusst nicht türkis und stehen immer mit Text oder Symbol.
  * Zurück zum bisherigen Aussehen: Werkzeugleiste unten rechts → „Original-Zustand“.
* **Logo:** Liegt `INNternat_Logo.png` im INNternat-Ordner (neben `modern_ui`), steht es unverändert oben in der
  Seitenleiste, auf dunklem Grund auf einer hellen Fläche. Ohne Datei steht dort der Schriftzug „INNternat“. Das Logo
  wird nicht ins Programm eingebaut.
* **Kontextleiste oben:** Sie zeigt nur die Unteransichten des gewählten Bereichs, z. B. bei Zimmer Übersicht ·
  Karten · Zeitstrahl · Liste · Defekte Zimmer · Änderungen. Dazu kommen Datenstand, Rückgängig, Neuigkeiten und
  Aufgaben. Die Hauptnavigation steht nur links.
* **Heute → Tageszentrale** (neue Standardansicht; Postfach und Übersicht bleiben als Umschalter):
  * Datum und eine Zeile, wie viel heute ansteht.
  * Kennzahlen: Jetzt klären, Anreisen heute (ohne Zimmer), Reinigung vor Einzug, Zimmer nicht nutzbar (mit
    Mängeln), frei nach Planung (Tiefstand). Jede Kennzahl ist ein Knopf zur passenden Stelle.
  * **Als Nächstes:** dringende und anstehende Aufgaben, nummeriert und nach Dringlichkeit sortiert, mit Bereich,
    direkter Aktion (bestehender Ablauf mit Prüfungen und Rückgängig), „Fälle ansehen“ (öffnet das Postfach an der
    Stelle) und „Später“.
  * **Die nächsten 7 Tage:** je Tag Anreisen (ohne Zimmer, x von y bezugsfertig) und Abreisen. Ein Klick öffnet die
    Anreise.
  * **Freie Zimmer nach Planung:** 5 Wochen als Balken, mit EMR und Doppelzimmern. Engpässe stehen zusätzlich als
    Text und Symbol da.
* **Outlook-Vorschau** (nur lesen): In den Einstellungen unter „Outlook-Vorschau auf ‚Heute‘“ den Ordner eintragen,
  z. B. `Internatsdienst` (Posteingang dieses Postfachs) oder `Internatsdienst/Posteingang/Anreisen`. Dann zeigt
  die Tageszentrale die neuesten 6 Mails mit Zeit, Betreff, Absender und „ungelesen“.
  * Es wird nichts gesendet, verschoben, gelöscht oder als gelesen markiert, und Outlook wird nicht gestartet.
  * Voraussetzung ist das klassische Outlook, das unter Windows läuft (derselbe Weg wie bei Erinnerungen und
    Briefing). Das neue Outlook hat diese Schnittstelle nicht.
  * Ohne Ordner zeigt der Block nur einen Hinweis und keine Inhalte.

## Postfach, Änderungen je Zeitraum, Schloss/Schlüssel als FM-Auftrag (neu in 0.37)

* **Postfach auf *Heute*** (wie Outlook, Standard in allen Layouts):
  * Links stehen die Aufgaben als Zeilen, gruppiert nach dringend, als Nächstes und zur Info. Rechts erscheinen
    alle Fälle der gewählten Aufgabe:
    * Planungen in unbewohnbaren Zimmern mit Ausweichvorschlag zum Anhaken.
    * Personen einer Anreise mit „Übernehmen“ je Person oder „Alle Vorschläge übernehmen“.
    * Zimmer, die vor dem Einzug noch gereinigt werden müssen, einzeln oder alle.
    * Allergiker, Widersprüche zum Gebäudeplan und FM-Aufträge.
  * Erledigtes verschwindet. Ist eine Aufgabe ganz erledigt, rückt die nächste nach. Mit den Pfeiltasten geht es
    hoch und runter.
  * Ganz oben steht „Überblick heute“ mit den Anreisen der nächsten 7 Tage, frei nach Planung, Abreisen und
    Reinigung.
  * Oben schaltet „Postfach | Übersicht“ auf die bisherige Ansicht zurück.
* **0.37.1:** Bei schmalem Fenster bricht die Leiste mit den Unteransichten jetzt um, statt unsichtbar abgeschnitten
  zu werden. Vorher fehlten dort z. B. „Änderungen“ oder „Defekte Zimmer“. In Showcase steht die Versionsnummer
  unten im Menü „Mehr“.
* **Zimmer → Änderungen:** Was im gewählten Zeitraum geändert wurde, als Tabelle:
  * Inhalt: Zuteilungen (geplant, umgeplant, entfernt, fest), Umzüge und Auszüge/Abbrüche, Mängel.
  * Zeiträume: Diese Woche, Letzte Woche, 7 Tage, 30 Tage oder frei von–bis.
  * Filter nach Art, sortierbar, Klick auf das Zimmer öffnet die Zimmerkarte.
  * **Excel** speichert die Liste mit Filter in den Spaltenköpfen.
  * Quelle ist das Änderungsprotokoll. Was nur im Gebäudeplan steht, ist dort nicht enthalten.
* **Tür/Schloss/Schlüssel defekt:**
  * Das Zimmer ist nicht nutzbar, das FM behebt es aber schnell. Deshalb wird **nicht umgeplant**, solange die
    Anreise noch 3 Tage oder mehr entfernt ist.
  * Stattdessen kommt die Aufgabe „Zimmer nicht nutzbar (Schloss/Schlüssel) – FM-Auftrag“ mit Frist, also dem
    nächsten Einzug. Dort lässt sich der Auftrag mit **FM-Auftrag kopieren** (ohne Namen, mit Frist) in eine Mail
    oder Teams einfügen. Nach der Reparatur markiert **Als behoben markieren** die Zimmer.
  * Wird es knapp (Anreise in weniger als 3 Tagen), ist die Aufgabe dringend, und der Fall kommt wieder zum
    Umplanen. Schimmel, Ungeziefer usw. werden wie bisher sofort umgeplant.

## Anreiselisten als PDF, Showcase aufgeräumt (neu in 0.36)

* **Anreiselisten Bad Pyrmont und Weser-Ems:** Dort kommen die Listen als PDF „Teilnehmer Beginn“ aus der
  Teilnehmerverwaltung. Sie werden unter *Daten & Import → Anreiselisten hochladen* eingelesen, mit
  Änderungsbericht vor dem Übernehmen wie bei den Excel-Listen.
  * **K** heißt: wohnt im Internat und braucht ein Zimmer. Personen ohne K werden mitgeführt, bekommen aber
    kein Zimmer.
  * **Anreise** ist das Eintrittsdatum der Person. Ein Sternchen markiert einen verspäteten Einstieg, das steht dann
    in der Bemerkung.
  * **Abreise** ist das Ende der Maßnahme.
  * **EMR** wird an der Maßnahme erkannt.
  * Geburtsdatum und Kostenträger werden **nicht** übernommen.
  * Die PDF hat keine TN-ID. Personen werden deshalb über Name und Anreisetag wiedererkannt.
* **Goslar bleibt bei den Excel-Listen:** Sie haben die TN-ID und die Bemerkungen (Allergiker, Hilfsmittel,
  Begleitung, Vortag), die die PDF nicht hat. Beide Formate zu mischen, würde Personen doppelt anlegen. Deshalb
  nimmt Goslar keine PDF-Listen an.
* **Showcase:**
  * Links im Dock steht jetzt der Standort, ein Klick darauf wechselt ihn.
  * Direkt sichtbar sind nur noch die fünf Hauptbereiche Heute, Anreisen, Zimmer, Reinigung und Auswertung.
    Termine, Assistenz, Mieter, Daten & Import, Inventar und Einstellungen liegen unter „Mehr“. Ein Punkt zeigt,
    wenn dort etwas offen ist.
  * Die Suche ist nur noch ein Symbol.
  * Die Kennzahlen sind kleiner und flacher.

## Drei Standorte: Goslar, Bad Pyrmont, Weser-Ems (neu in 0.35)

Beim Start fragt die Oberfläche: **Welcher Standort?** Vorausgewählt ist der zuletzt gewählte, Enter genügt.
Gewechselt wird jederzeit über das Logo oben links, wo unter „Belegung“ der aktuelle Standort steht.

* **Getrennte Verwaltung:** Heute, Anreisen, Zimmer, Reinigung, Termine, Mieter, Inventar sowie Daten & Import
  gelten nur für den gewählten Standort. Jeder Standort hat einen eigenen Datenordner. Goslar bleibt, wo es immer
  war. Bad Pyrmont liegt in `Standorte\BP`, Weser-Ems in `Standorte\WE`. Jeder Ordner hat eigene Eingangsordner
  (`Gebaeudeplan`, `Listen`, `UWT`), eigene Sicherungen, eigenen Verlauf und eigenes Rückgängig. Beim Wechsel wird
  das Rückgängig geleert, damit nie ein Schritt im falschen Standort zurückgenommen wird.
* **Auswertung und Prognose bleiben wie bisher:** Sie zeigen immer alle drei Standorte und lesen weiter aus dem
  Goslar-Ordner (Belegungs-Pivot, Kapazitäten, Statistik). Diese Quellen pflegt man im Standort Goslar. Die
  Darstellung (Layout und Farben) gilt für alle Standorte.
* **Gebäudeplan:** Den Export aus dem Belegungssystem wie gewohnt unter *Daten & Import → Gebäudeplan hochladen*
  einlesen, im jeweiligen Standort. Bad Pyrmont („BP-A 103“, Gebäude A–D, UG bis 6. OG) und Weser-Ems
  („WE-A 202 R“, Internat A–G, UG bis 3. OG) werden mit Häusern, Etagen, Betten, Belegungen und Sperrungen erkannt.
  Gebäudeskizzen sind dafür nicht nötig.
* **Zimmer eingeben:** Die Zimmerprüfung versteht „A 103“, „a103“ oder „A-202-R“, je nach Standort.
* **Regeln:** Die Zuteil-Regeln des Hauptprogramms sind auf Goslar zugeschnitten. In Bad Pyrmont und Weser-Ems
  gelten zunächst neutrale Regeln: Alle Zimmer stehen allen Gruppen offen. Doppelzimmer sind nur für UWT und
  Gäste, Gästezimmer nur für Gäste. Tier-Zimmer, „nur Männer“ und „außer Betrieb“ gelten so, wie sie in den
  Zimmer-Stammdaten markiert sind. Eigene Regeln je Standort (Allergiker-, Tier-, Gästezimmer …) kommen nach und
  nach dazu.
* **Daten & Import** zeigt in Bad Pyrmont und Weser-Ems zunächst nur Anreiselisten und Gebäudeplan. UWT,
  Schlüssellisten, ZKL und Zimmer-Pivot sind auf die Goslarer Listen zugeschnitten und kommen dazu, sobald es die
  Listen der Standorte gibt.
* **In Goslar ändert sich nichts.** Das Hauptprogramm bleibt unverändert und kennt weiterhin nur Goslar.

## Ergebnisse der UX-Prüfung (neu in 0.34)

Eine externe UX/UI-Prüfung hat sechs Punkte gefunden. Alle sind umgesetzt:

* **Nichts geht beim Schließen verloren:** Wer in einem Panel (z. B. *Neuer Mieter*) etwas eingegeben oder angehakt
  hat und es mit Esc, ✕ oder einem Klick daneben schließt, wird gefragt: *Eingaben verwerfen?* Die Antwort
  „Weiter bearbeiten“ (oder Esc) behält alles. Ohne Eingaben schließt das Panel wie bisher sofort. „Abbrechen“ im
  Formular verwirft weiterhin ohne Rückfrage.
* **Lesbarere Kleinschrift:** Spaltenköpfe, Hinweise und Datumsangaben sind heller (Kontrast mindestens 4,5:1 auf
  allen Flächen, WCAG). Das Layout ist unverändert.
* **Datenstand sichtbar:** In der Kopfzeile steht „Stand 14:32“, also wann die Daten zuletzt geladen wurden. Hat das
  Hauptprogramm gespeichert, wird neu geladen und die Anzeige leuchtet kurz auf. Ist gerade ein Formular offen, steht
  dort „· neue Daten“ (orange); neu geladen wird nach dem Schließen.
* **Bericht nach dem Einlesen beim Start:** Neue Dateien in den Ordnern „Listen“ und „UWT“ werden wie im
  Hauptprogramm beim Start übernommen. Die Meldung nennt jetzt, wie viele Personen neu sind, wie viele
  geändert oder entfallen sind und wie viele geplante Zimmer betroffen sind. Mit *Was hat sich geändert?* öffnet sich
  der Änderungsbericht. Dort gibt es „Rückgängig machen“ und den Sprung zu den Anreisen. Das gilt auch für *Daten &
  Import → Ordner jetzt einlesen*.
* **Sortieren per Tastatur:** Die Spaltenköpfe sind mit Tab erreichbar. Enter oder Leertaste sortiert, und
  Bildschirmleser hören Spalte und Richtung.
* **Weitere Darstellungen:** Standard bleibt „Original“. Layouts und Farben stehen nur noch unter *Weitere
  Darstellungen*, in der Werkzeugleiste unten rechts als ein Knopf und in den Einstellungen eingeklappt. Dass ein
  anderes Theme auch das Layout zu Classic Grid wechselt, steht direkt dabei. Hell/Dunkel und Dichte erscheinen
  nur in den weiteren Darstellungen.

## Auf einen anderen PC umziehen (neu in 0.33.1)

* Den ganzen Ordner `INNternat` kopieren (am besten an denselben Pfad), auf dem neuen PC Python 3.11+ installieren und
  `modern_ui\Start.bat` starten. Eine mitkopierte Python-Umgebung (`modern_ui\.venv`) passt nicht zum neuen PC –
  `Start.bat` erkennt das jetzt selbst, löscht sie und legt sie neu an (vorher: Meldung „did not find executable …“).
* **Python-Version (0.33.2):** Für ganz neue Versionen (z. B. 3.15) gibt es oft noch keine fertigen Pakete – die
  Installation bricht dann ab („Microsoft Visual C++ 14.0 … required“). `Start.bat` nimmt deshalb bevorzugt Python
  3.13, dann 3.12, 3.11, erst danach die neueste. Empfehlung: Python 3.13 installieren (python.org oder
  `py install 3.13`), `modern_ui\.venv` löschen, neu starten.

## Abbruch / vorzeitiger Auszug (neu in 0.33)

* In der **Zimmerkarte** bei jeder Person, die schon im Zimmer wohnt: **„Auszug / Abbruch …“** – letzten Tag im
  Zimmer und Grund (Abbruch, vorzeitiger Auszug, sonstiges) wählen, **Auszug buchen**.
* Gekürzt wird in einem Schritt überall: Abreise in der Anreiseliste (Grund kommt in die Bemerkung), die eigene
  Planung und – bis zum nächsten Gebäudeplan – die Buchung im gespeicherten Gebäudeplan. Vorher blieb das Zimmer
  belegt, solange der Gebäudeplan die alte Abreise zeigte. Danach ist das Zimmer frei und kommt auf die
  Reinigungsliste. Rückgängig ist möglich; im Belegungssystem bitte ebenfalls buchen.
* Mieter: Vertragsende auf der Seite *Mieter*. Kommt jemand gar nicht: *Anreisen → Person entfernen*.
* Zimmerhistorie: übernimmt jetzt auch ein früheres Ende (nach Abbruch) statt der ursprünglich geplanten Abreise.

## Planung widerspricht dem Gebäudeplan – nie mehr still „frei“; Schlüssellisten abgleichen (neu in 0.32)

* **Fehler behoben (schwerwiegend):** Stand eine Person im Gebäudeplan in einem anderen Zimmer als in der eigenen
  Planung, galt still der Gebäudeplan (Regel des Hauptprogramms) – das geplante Zimmer erschien **frei**, obwohl
  Zuteilen und Suche es weiter zeigten. War der Gebäudeplan veraltet, drohte eine Doppelbelegung.
* Jetzt: dringende Karte **„Planung widerspricht dem Gebäudeplan“**, Hinweis in der Zuteilung, ein Kasten in der
  Zimmerkarte, gestrichelter Rahmen mit „?“ in der Übersicht und „⚠ strittig – Gebäudeplan: …“ in der Suche.
  Bis zur Klärung wird das geplante Zimmer **niemand anderem** angeboten (Zuteilen, Vorschläge, Ziehen im Zeitstrahl,
  Zimmer prüfen, Person hinzufügen, Ausweichzimmer).
* Klären per Klick: **Gebäudeplan stimmt** (eigene Planung wird auf dessen Zimmer gesetzt) oder **Planung stimmt**
  (gilt dann auch gegen den Gebäudeplan; dessen Zimmer wird frei – im Belegungssystem umbuchen). Mit Rückgängig.
* **Schlüssellisten abgleichen** (*Daten & Import*): die An- und Abreiselisten vom Empfang (Anreise, Abreise, An, Ab,
  Zimmer, Name …) hochladen – wo der Schlüssel ausgegeben wurde, wohnt die Person. Je Zeile: stimmt / korrigieren /
  nur im Gebäudeplan (im Belegungssystem umbuchen) / nicht gefunden; Hinweis, wenn laut Programm noch jemand anderes
  im Zimmer ist. Korrekturen für laufende Aufenthalte sind vorausgewählt; übernommen wird nur das Angehakte (Planung
  „fest“ und mit Vorrang vor dem Gebäudeplan), ein Rückgängig für alles.

## Bestimmtes Zimmer prüfen (neu in 0.31)

* In den **Personenangaben** (Klick auf den Namen in Zuteilen): Feld **„Bestimmtes Zimmer prüfen“** – Zimmer
  eingeben (z. B. „3.2-111“, „3.2 111“) und „Prüfen“. Das Programm sagt, ob das Zimmer passt, nur als Ausnahme geht
  (z. B. „nur Kurzmaßnahmen“) oder warum nicht – mit allem, was im Zeitraum im Weg ist (wer, von wann bis wann,
  Gebäudeplan oder eigene Planung, Reinigungsabstand).
* Passt es oder geht es als Ausnahme: **Zuweisen** bzw. **Trotzdem zuweisen** direkt dort.
* Nie möglich (wie im Hauptprogramm): unbewohnbare Zimmer, belegte/gesperrte Zeiträume, fremde Mitbewohner und
  Doppelzimmer für andere als UWT und Gäste. Ist ein Zimmer im Gebäudeplan fälschlich als Doppelzimmer geführt,
  hilft *Einstellungen → Zimmer-Stammdaten*.

## Meldungen anklicken, Ausweichzimmer erst prüfen (neu in 0.30)

* **Klick auf den Text einer Karte** (Heute und Aufgaben) zeigt alle betroffenen Fälle statt nur der ersten zwei,
  drei Namen – z. B. alle Allergiker mit Anreise, Zimmer und „auf der Etage ✓“, oder alle Planungen in
  unbewohnbaren Zimmern. Bei anderen Karten führt der Klick an die passende Stelle.
* **„Prüfen und zuweisen“** (vorher „Ausweichzimmer zuweisen“): Liste aller Planungen mit Konflikt bzw. in
  unbewohnbaren Zimmern – Person, Anreise, Zimmer jetzt mit Grund, vorgeschlagenes Ausweichzimmer (beide Zimmer
  anklickbar). **Umgeplant wird nur, was angehakt ist** (oder „Alle mit Vorschlag auswählen“), ein Rückgängig für alles.
* Wer **schon eingezogen** ist, bekommt kein Ausweichzimmer vorgeschlagen – das wäre ein Umzug (Zimmerkarte →
  Umzug planen).
* **Fehler behoben:** Die Ausweichzimmer wurden je Person einzeln gesucht – mehrere Personen konnten dasselbe Zimmer
  bekommen (im Test landeten 5 Personen im selben Zimmer). Jetzt werden sie gemeinsam verteilt: kein Zimmer doppelt
  für denselben Zeitraum.

## Zimmerhistorie, deutlichere Zimmerfarben, flexible Mietverträge (neu in 0.29)

* **Zimmerhistorie:** Die neue Oberfläche merkt sich bei jedem Laden, wer wann in welchem Zimmer gewohnt hat (laut
  Gebäudeplan und eigener Planung) – auch wenn die Person später aus Gebäudeplan und Listen verschwindet. Die
  Zimmerkarte zeigt **„Früher in diesem Zimmer“**, die Suche (**Strg+K**) findet ehemalige Bewohner mit Zimmer und
  Zeitraum. Beim ersten Start wird aus den automatischen Sicherungen nachgetragen (so weit sie zurückreichen).
  Umgeplante oder vor der Anreise gestrichene Planungen bleiben nicht hängen. Aufbewahrt wird 5 Jahre nach dem
  Auszug, danach wird automatisch gelöscht. Gespeichert in `importe/modern_zimmerhistorie.json` (wird mitgesichert).
* **Zimmerfarben:** frei, belegt und geplant waren kaum zu unterscheiden (belegt und geplant fast dieselbe Farbe).
  Jetzt: **frei** kräftigeres Grün, **belegt** helleres Blau, **geplant** hohl mit gestricheltem Rand – auch bei
  Farbsehschwäche unterscheidbar, Schrift gut lesbar. Gilt für Übersicht, Zeitstrahl, Legenden und alle Layouts.
* **Flexible Mietverträge** (*Mieter → Neuer Mieter → „Flexibler Mietvertrag“*, sonst aus): Die abweichenden
  Textstellen stehen in `Vorlagen/Mieter/Mietvertrag.vorlage` als eigene Zeilen – `?flexibel <Text>` nur im flexiblen,
  `?!flexibel <Text>` nur im üblichen Vertrag (wie `?kaution`). Fehlen die Textstellen, wird kein flexibler Vertrag
  erstellt (klare Meldung). Welche Verträge flexibel sind, merkt sich das Programm für „Unterlagen neu erstellen“.
  Das Hauptprogramm erstellt weiterhin immer den üblichen Vertrag.

## Sortieren per Klick auf die Spaltenüberschrift (neu in 0.28)

* In allen Listen mit Kopfzeile (Zuteilen, Personen, Abreisen, Firmenprogramm, Zimmer-Liste, Defekte Zimmer – je
  Dringlichkeit für sich –, Reinigung, Inventar, Zimmer-Stammdaten …): Klick auf eine Überschrift sortiert aufsteigend (▲), nochmal absteigend (▼), ein drittes Mal
  wieder wie vorher.
* Daten werden als Datum sortiert (Zeitraum: erst Beginn, dann Ende), Zahlen als Zahl, Zimmer „natürlich“
  (2-9 vor 2-10); leere Felder stehen immer am Ende.
* Die Wahl bleibt erhalten, solange das Fenster offen ist – auch nach Änderungen und beim Zurückwechseln.
* Spalte „Gruppe“ etwas breiter, damit „Vorb.“, „Haupt“ und „Mieter“ ganz zu sehen sind.

## Gruppen: Hauptmaßnahme, vorbereitende Maßnahme, Assessment, UWT, Gast, Mieter (neu in 0.27)

* **Neue Person anlegen** (Zimmerkarte → Person hinzufügen): kein Feld „Maßnahme“ mehr. Gewählt wird nur die
  Gruppe – Hauptmaßnahme, vorbereitende Maßnahme, Assessment, UWT, Gast oder Mieter. Details wie die genaue Maßnahme
  (z. B. FIAE, iBTZ) oder eine Hospitation gehören in die Bemerkung.
* **Personenangaben** (Klick auf den Namen): dieselben Gruppen, dazu EMR. RVL wird weiter erkannt und gilt als
  vorbereitende Maßnahme (mit der Vorliebe für Haus 3.1); gespeichert wird nur, wenn die Gruppe wirklich umgestellt wird.
* Spalte **Gruppe** in Zuteilen und Personen: „Haupt“, „Vorb.“, „ASS“, „EMR“, „UWT“, „Gast“, „Mieter“.
* Die Zuteilungsregeln bleiben die des Hauptprogramms (Hauptmaßnahme = bisher „Reha-Maßnahme“, vorbereitende Maßnahme
  = RVL/RVT).

## Flur-Raster: Abreisewellen je Flur (neu in 0.26, zum Ausprobieren)

* *Zimmer → Zeitstrahl → Umschalter „Zimmer | Flure“* (zweite Zeile). In der Fluransicht steht je Flur (Haus,
  Etage, West/Ost) eine Zeile, je Woche eine Spalte (4/8/12 Wochen). Die Zahl im Feld sagt, zu wie vielen
  **Abreisewellen** die belegten Zimmer gehören – grün 1, gelb 2, rot 3 und mehr. Wenige Wellen heißt wenige
  Reinigungsanlässe und Übergaben auf dem Flur.
* **Abreisewelle:** Zimmer, die im selben Reinigungsfenster ganz frei werden – Wochenende zählt zum Montag, eine Welle
  umfasst höchstens zwei aufeinanderfolgende Werktage ab dem ersten Auszug (Fr + Mo = eine Welle, Di + Fr = zwei).
  Doppelzimmer zählen erst, wenn beide ausgezogen sind.
* **Gewertet** werden lange Aufenthalte. Kurze (EMR, ASS, UWT, Gäste, bis 8 Wochen) und Mieter stehen klein im Feld
  („5 kurz“, „1 M“) und machen einen Flur nicht schlechter.
* Klick auf ein Feld: die Wellen dieser Woche mit Zimmern, Namen und Zeiträumen, dazu kurze Aufenthalte und Mieter;
  „Zimmer im Zeitstrahl zeigen“ öffnet den Zeitstrahl nur für diesen Flur (Filter oben mit ✕ aufheben).
* Die Ansicht zeigt nur – sie verschiebt nichts und ändert keine Daten. Bringt sie nichts, kommt sie wieder raus.

## Vertragsnummern der Mieter mit bisherigen Verträgen abgleichen (neu in 0.25)

* Bisher zählte die Nummer nur die Verträge, die mit diesem Programm erstellt wurden – im neuen Jahr also ab
  „26-001“, obwohl es schon Verträge gab. Jetzt wird abgeglichen mit: der Mieterliste, den Dateien im Ablageordner
  der Unterlagen, einem **Ordner mit den bisherigen Verträgen** (auch Unterordner; Nummer im Dateinamen, z. B.
  „MV 26-047 …“, „Mietvertrag_26.047 …“) und einer von Hand festgelegten **zuletzt vergebenen Nummer**. Vorschlag ist
  die höchste Nummer des Jahres + 1; darunter steht, woher sie stammt.
* Einstellen unter *Mieter → Neuer Mieter → „Nummern mit bisherigen Verträgen abgleichen“*.
* Eine schon vergebene Nummer (auch aus einer Datei) lässt sich nicht noch einmal verwenden – die Meldung nennt die
  nächste freie.

## Tagesbriefing per Outlook, Allergiker mit Vorrang auf der Allergiker-Etage (neu in 0.24)

* **Tagesbriefing** (*Einstellungen → Allgemein → Erinnerungen*): einmal am Tag ab der eingestellten Uhrzeit die
  wichtigsten Punkte – wahlweise als **Outlook-Termin** (mit Erinnerung, als „frei“ eingetragen) oder als **E-Mail an
  mich**. Inhalt: Dringendes zuerst, „als Nächstes“, Anreisen heute/morgen mit „x von y bezugsfertig“, Abreisen,
  Reinigung, freie Zimmer, Allergiker, Anzahl fälliger Termine und offener Mails. **Ohne Personennamen** – Details
  stehen im Programm. *Vorschau* zeigt den Text, *Jetzt testen* schickt ihn sofort (zählt nicht als heutiges).
  Geprüft wird beim Start und alle 15 Minuten; klappt der Versand nicht (Outlook zu), wird es an dem Tag nicht
  ständig wiederholt – die Zeile darunter zeigt den letzten Stand. Nur unter Windows mit Outlook (klassisch).
* **Allergiker haben Vorrang auf der Allergiker-Etage (Haus 2, 1. OG):** Die Etage ist für sie da, Allergiker sind
  selten – deshalb werden sie dort bevorzugt eingeplant, auch bei langen Maßnahmen und auch in 101–110 (sonst nur
  EMR). Die Etagen-Regeln erzeugen für Allergiker keine Warnung mehr; „Optimieren“ zieht sie nicht von der Etage weg.

## Hinweise aus den Anreiselisten, Allergiker-Etage, Bereitschaft, Reinigungsvorschau (neu in 0.23)

* **Hinweise aus der Anreiseliste** (Spalte „Internatsdienst“): Beim Zuteilen stehen kleine Marken am Namen –
  *Allergiker*, *Hilfsmittel* (z. B. Duschhocker, Rollator), *Begleitung* (z. B. Ehemann im DZ), *evtl. Vortag*;
  sonstiger Text als *Hinweis*. Der volle Text steht beim Überfahren. Das bei EMR übliche „ev. Anr.“ erzeugt
  bewusst keine Marke (EMR werden ohnehin ab dem Vortag geplant).
* **Allergiker-Etage (Haus 2, 1. OG):** Für Allergiker schlägt die Zuteilung dort ein freies, nach den Regeln
  zulässiges Zimmer vor – nie eines mit gemeldetem Schimmel, Ungeziefer, Geruch oder verschmutztem Boden. Liegt die
  Planung woanders, wird gewarnt (mit Ausweichvorschlag, falls frei). Eigene Meldung: Karte unter *Heute*
  (dringend, wenn die Anreise in 7 Tagen ist und das Zimmer nicht passt) und einmal je Person eine Windows-Meldung.
  Seit 0.24 haben Allergiker dort Vorrang: Die Regeln „1. OG nur Kurzmaßnahmen“ und „101–110 nur EMR“ gelten für sie nicht.
* **Bezugsfertig je Anreise** (*Anreisen*, Kachel „x von y bezugsfertig“): Zimmer gespeichert, kein Konflikt,
  Reinigung vor genau dieser Anreise erledigt. Klick zeigt, was fehlt und was vorzubereiten ist (Hilfsmittel,
  angekündigte Begleitung, offene Mängel). Auch auf der Anreise-Karte unter *Heute*.
* **Reinigung:** „Mehrere abhaken“ – alle sichtbaren, je Haus oder je Flur (mit Rückgängig). Neue Ansicht
  **Vorschau 6 Wochen**: Zimmer je Tag und Haus, Spitzentage markiert (gezählt werden Zimmer, nicht Arbeitszeit).
* **Zimmer-Übersicht:** neue Kachel **nicht bezugsfertig** (frei, aber Reinigung der letzten 14 Tage offen oder
  dringender Mangel), Besen an der Kachel; auch kombinierbar, drucken und Excel.
* **Anreiselisten-Import mit Änderungsbericht:** vor dem Übernehmen steht, was sich gegenüber dem jetzigen Stand
  ändert – geänderte An-/Abreisen (alt → neu), Internat, neue Hinweise (z. B. Allergiker), wer nicht mehr auf der
  Liste steht, wer neu ist; geplante Zimmer, die davon betroffen sind, stehen oben und sind markiert.

## Zähler an den Menüpunkten, Glocke, Haptik (neu in 0.22)

* **Zähler an den Menüpunkten** (Seitenleiste und Dock), wie im Hauptprogramm: *Termine* (fällige Erinnerungen),
  *Mieter* (Verträge, die in den nächsten 6 Wochen enden), *Assistenz* (offene Mails), *Reinigung* (offen, obwohl
  jemand einzieht – rot), *Anreisen* (geplante Zimmer, die laut Gebäudeplan inzwischen belegt/gesperrt sind – rot).
  Beim Überfahren steht dran, was gezählt wird.
* **Glocke** oben neben „Aufgaben“: zählt ungelesene Neuigkeiten (dieselben wie im Hauptprogramm). Klick öffnet die
  Liste – ungelesene sind markiert; ein Klick auf eine Neuigkeit markiert sie als gelesen und springt dorthin,
  „Alle als gelesen markieren“ leert den Zähler.
* **Haptik – Eingaben mit Gewicht** (in den Layouts; der Original-Zustand bleibt wie er war): Knöpfe heben sich beim
  Überfahren leicht an und geben beim Drücken spürbar nach wie eine Taste; Kacheln, Umschalter und Menüpunkte drücken
  sich ein. Solange gespeichert wird, läuft oben ein schmaler Balken; danach rastet die Bestätigung mit einem Haken
  ein. Eingabefelder bekommen beim Hineinklicken einen deutlichen Ring, Schalter federn nach. Ist in Windows
  „Animationen reduzieren“ an, bleibt es bei Farbwechseln.

## Letzte Funktionen aus dem Hauptprogramm: Pivot-Struktur, Einfügen, Windows-Meldungen, Autostart (neu in 0.21)

Damit kann die neue Oberfläche alles, was das bisherige Programm konnte.

* **Pivot-Struktur** (*Daten & Import → Pivot → Pivot-Struktur …*): nur nötig, wenn eine Pivot-Datei anders aufgebaut
  ist als üblich – Tabellenblatt (automatisch oder fest), Ausrichtung, Ebenen, Kopfzeilen-Text, Zwischensummen-Endung,
  Datumsformat. Die Vorschau zeigt sofort, ob es passt (Tage, Zeitraum, Häuser je Standort); gespeichert wird nur, was
  passt. Rückgängig ist möglich. Es ist dieselbe Einstellung wie im Hauptprogramm.
* **Gebäudeplan aus der Zwischenablage** (*Daten & Import → Gebäudeplan → Aus Zwischenablage einfügen …*): im
  Belegungssystem die Gebäudeansicht markieren (Strg+A) und kopieren (Strg+C), ins Feld klicken, Strg+V – danach
  derselbe Abgleich wie beim Hochladen der Word-Datei.
* **Windows-Meldungen** (*Einstellungen → Allgemein → Erinnerungen*): fällige Termine, offene Reinigung vor einer Anreise
  und Facility-Checks erscheinen unten rechts als Windows-Meldung und unter Neuigkeiten – kurz nach dem Start und
  alle 15 Minuten, jede Meldung nur einmal, auch wenn das Hauptprogramm gleichzeitig läuft. Abschaltbar.
* **Mit Windows starten**: legt eine Verknüpfung im Autostart an; die neue Oberfläche startet dann minimiert und meldet
  Fälliges, ohne dass man sie öffnen muss. Ausschalten entfernt die Verknüpfung wieder.
* **Behoben:** Ein Klick in die Navigation direkt nach dem Start (während die Daten noch ankamen) ging manchmal
  verloren – die Navigation bleibt jetzt stehen und aktualisiert nur noch die Zahl an „Heute“.

## Kalender zum Anklicken, Ordner-Import, Klassenstärken, Ziehen im Zeitstrahl (neu in 0.20)

* **Termine → Monat:** Ein Klick auf einen Tag legt dort einen Termin an (beim Überfahren erscheint „+“; Titel
  eingeben, Enter speichert). Ein Klick auf einen Eintrag öffnet ihn – eigene Termine zum Bearbeiten, Anreisen,
  Abreisen und UWT zum Ansehen und Abhaken. „+N weitere“ zeigt alle Einträge des Tages.
* **Automatischer Import wie im Hauptprogramm:** Beim Start werden neue Dateien in den Ordnern „UWT“ (Blockpläne,
  Kalender, Klassenübersicht) und „Listen“ (Einheitslisten) eingelesen – schon gelesene Dateien (auch vom
  Hauptprogramm) werden übersprungen, Rückgängig ist möglich. Unter *Daten & Import* gibt es dazu „Ordner jetzt
  einlesen“. Liegt ein neuer Gebäudeplan im Ordner „Gebaeudeplan“, erscheint unter *Heute* eine Karte.
* **Klassenstärken (UWT):** Beim Import eines Blockplans (PDF ohne Personenliste) stehen die Klassen mit ihrer Anzahl
  im Internat zum Ändern da (0 = zählt nicht); die Vorschau rechnet sofort mit. Dauerhaft änderbar unter
  *Daten & Import → UWT → Klassenstärken …*.
* **Zeitstrahl:** Geplante Personen (noch nicht eingezogen) lassen sich mit der Maus in eine andere Zimmerzeile ziehen.
  Geprüft wird wie im Hauptprogramm (belegt, gesperrt, fremder Mitbewohner = geht nicht; Regelverstoß = Ausnahme mit
  Hinweis); vor dem Speichern „vorher → nachher“, beim DZ-Partner „Beide wechseln“ oder „Nur …“. Wer schon
  eingezogen ist, zieht wie bisher über „Umzug planen“ um.

## Übersicht: mehrere Kacheln, Filter nach Mangelart (neu in 0.19)

* **Mehrere Kacheln gleichzeitig:** Jeder Klick nimmt eine Kachel dazu oder wieder weg. Die Status-Kacheln (frei,
  belegt, geplant, gesperrt) gelten mit „oder“ – *frei + geplant* zeigt beide. *Mit Mängeln* und *unbewohnbar*
  schränken zusätzlich ein – *frei + mit Mängeln* zeigt die freien Zimmer, die Mängel haben. „Zurücksetzen“ hebt alles auf.
* **Mangelart** (Knopf neben den Kacheln, auch unter *Defekte Zimmer*): Stufe (rot/orange/gelb) und/oder Art
  (Heizung, Schimmel, Fenster …), mehrere wählbar. Die Auswahl ist dieselbe wie *Filter → Mangel* in Karten und Liste
  und gilt damit in allen Zimmer-Ansichten, bis sie aufgehoben wird.
* Drucken und Excel aus der Übersicht nehmen genau diese Auswahl (Überschrift z. B. „frei oder geplant · mit Mängeln ·
  Mangel: Heizung defekt“).

## Zimmer drucken und als Excel – mit „frei bis“ (neu in 0.18)

Unter **Zimmer** gibt es „Drucken & Export“ jetzt in der **Übersicht** und weiterhin in **Karten**/**Liste**. Gedruckt
bzw. exportiert wird immer genau die aktuelle Auswahl:

* **Übersicht** – alle Zimmer oder nur die angeklickte Kachel (frei, belegt, geplant, gesperrt, mit Mängeln,
  unbewohnbar), Status am gewählten Tag.
* **Karten / Liste** – die gesetzten Filter (Haus, Status, Schnellfilter, Suche, weitere Filter).

Je Zimmer: Status am Stichtag, Bewohner (oder „ohne Namen“), **belegt bis**, **frei ab**, **frei bis** und **freie Tage**.
„frei bis“ ist der letzte freie Tag vor der nächsten bekannten Belegung (Puffer nach Abreise berücksichtigt);
„offen“ heißt: keine Folgebelegung bekannt. Bei belegten Zimmern zeigt „frei ab“ den ersten freien Tag nach dem Auszug.
Die Excel-Datei (Ordner *Export*) ist sortier- und filterbar, freie Zimmer sind grün hinterlegt; der Druck öffnet
die Druckansicht im Browser (dort drucken oder als PDF speichern).

## Prognose in drei Bereichen – Dashboard ohne Scrollen (neu in 0.17)

Oben links wählt man den Bereich (die Leiste mit Präsentation und Export):

* **Dashboard** – nur das Wesentliche, passt ohne Scrollen auf einen Laptop-Bildschirm (geprüft 1440×900 und
  1366×768, auch in den Layouts Canvas und Showcase): Filterleiste, der Graph (er nimmt den verbleibenden Platz ein),
  fünf kompakte Kennzahlen und die drei wichtigsten Erkenntnisse als schmale Badges (ganzer Text beim Überfahren,
  „+N“ führt zu allen). Läuft eine Simulation, erscheint „Szenario aktiv“ als Sprung zum Szenario.
  „Aufbau abspielen“ und „Optionen“ stehen als Symbole rechts in der Filterleiste.
* **Szenarien & Simulation** – links der Graph mit der Schattenkurve, rechts das Management-Szenario (Pills, Stepper,
  Ausgang ↔ Szenario); bei Goslar darunter UWTler, Mieter und die Kontingent-Planung.
* **Details & Protokoll** – aufklappbare Abschnitte: *Monate im Detail* (offen), *Erkenntnisse – vollständig*,
  *Standortvergleich*, *So wurde gerechnet & Backtest*.

Die Präsentation (Taste P) bleibt wie bisher. Die Legende des Graphen bleibt einzeilig (blättert bei Platzmangel).

## Ansicht steuert den Personenkreis, eine Filterleiste (neu in 0.16)

* **„Belegung“ = reine Teilnehmer-Sicht, „Nach Status“ = inklusive UWTler und Mieter.** Die Ansicht am Graph
  bestimmt jetzt, wer gezählt wird – Kurve, Kennzahlen, Erkenntnisse, Reserve, Vorjahr, Tabelle, Standortvergleich und
  Exporte folgen ihr (bei Goslar und Gesamt; Bad Pyrmont und Weser-Ems haben keine UWTler und Mieter). Die bisherigen
  Schalter „UWTler / Mieter einbeziehen“ im Optionen-Menü entfallen. Die Goslar-Detail-Einheit zeigt UWTler, Mieter und
  Kontingente immer mit echten Zahlen.
* **Badge über dem Graph:** bei „Nach Status“ **leuchtet** „Ansicht: Inklusive UWTler und Mieter“ (Akzent-Rahmen,
  leichter Schein), bei „Belegung“ steht gedämpft „Ansicht: Reine Teilnehmer-Sicht“. Der Badge wechselt im selben
  Moment wie der Graph; die Kennzahlen ziehen ohne Flackern nach.
* **Eine Filterleiste direkt über dem Graph:** links die Standorte (Gesamt · Bad Pyrmont · Goslar · Weser-Ems),
  rechts gebündelt Netto/Brutto und der Zeitraum (12M · 24M · 36M). Oben bleiben nur Präsentation und Export.
  Standorte und Reiter stehen bündig links.

## Heute als Newsfeed, Briefing, Drawer, Tempo (neu in 0.15)

In allen neuen Layouts (Canvas, Showcase, Grid – jedes Theme); im Layout **Original** bleibt alles 1:1 wie bisher.

* **Heute als Newsfeed:** ein aufgeräumter, chronologischer Strom mit nur dem Wesentlichen – **Jetzt** (dringende
  Aufgaben mit 1-Klick-Lösung, Warnungen), **Heute** (Anreisen mit „ohne Zimmer“, Abreisen, eilige Reinigung) und
  **Morgen**. Alles andere steckt hinter „N weitere Aufgaben“ im Drawer. Oben drei Kennzahlen: Zimmer frei, Anreisen
  ohne Zimmer, dringende Aufgaben.
* **Briefing abspielen** (Wellen-Symbol oben im Kopf): liest in rund 30 Sekunden die drei wichtigsten Fakten vor –
  Anreisen (und wie viele ohne Zimmer), freie Zimmer, dringende Aufgaben – mit der Sprachausgabe von Windows/Edge.
  Es verlässt nichts den Rechner, es werden keine Namen vorgelesen. Die Mitschrift erscheint dabei unter dem Kopf,
  der aktuelle Satz ist hervorgehoben; ein zweiter Klick beendet.
* **Aufgaben-Drawer** rechts: Glas-Optik (stark weichgezeichnet, fast schwarz bzw. im hellen Modus fast weiß),
  flüssig scrollbar, Gruppenköpfe bleiben stehen, dringende Karten mit feiner roter Linie links, **„Später“ als
  Symbol** (Wecker) im Kartenkopf. Während der Drawer offen ist, tritt die Werkzeugleiste zurück.
* **Diagramme ohne Wartezeit:** Reiter (Trend · Reserve · Vorjahr) und Ansichten (Belegung · Nach Status · Standorte
  parallel) schalten **im Browser** um – alle Ansichten liegen fertig vor (gemessen 14–30 ms statt 0,3–2 s).
  Standort, Netto/Brutto und Zeitraum rechnen nur noch die Seite neu (nicht Zimmerplan und Aufgaben), die Prognose
  wird einmal je Datenstand gerechnet (680 → 46 ms, danach aus dem Zwischenspeicher) und die übrigen Standorte im
  Hintergrund vorbereitet; der Knopf schaltet sofort um (gemessen 0,2–0,3 s bis zum neuen Graph statt 1,2–1,9 s).
* **Aufgeräumte Kontrollen:** keine Checkboxen mehr über dem Graph. **Backtest**, **95 %-Band** und die Animation stehen im Menü **Optionen** (UWTler/Mieter seit 0.16 über die Ansicht); über dem Graph zeigt ein Status-Badge, was gerade
  einbezogen ist („Ansicht: Inklusive UWTler und Mieter“ bzw. „Reine Teilnehmer-Sicht“, dazu „Backtest an“).

## Geführter Aufbau, Standorte parallel (neu in 0.14)

* **Geführter Aufbau des Prognosegraphen** (beim Öffnen, beim Wechsel des Reiters bzw. der Ansicht und mit
  „Aufbau abspielen“ – nicht bei Filterwechseln; aus bei „Bewegung reduzieren“ im System oder unter *Optionen*):
  1. das **Ist** zeichnet sich von links auf,
  2. der **Stichtag-Marker** trennt Vergangenheit und Zukunft, der laufende Monat erscheint,
  3. die **Prognose** zieht sich weiter, danach **fächern sich die 80/95 %-Bänder** vom Prognosestrich aus auf,
  4. **Spotlight-Badges** markieren die wichtigsten Punkte der nächsten 12 Monate: Höchststand (mit Auslastung) und
     der erste Engpass – oder, wenn es keinen gibt, der Tiefpunkt.
  Alles mit Ease-out; die Achse bleibt dabei fest. Die Badges stehen auch ohne Animation im Graph.
* **Ansicht-Badge über dem Graph** folgt sofort den Schaltern: „Ansicht: Inklusive UWTler und Mieter“,
  „… Inklusive UWTler“, „… Inklusive Mieter“ oder „Ansicht: Reine Teilnehmer-Sicht“.
* **Standorte parallel** (nur bei *Gesamt*, Schalter „Ansicht“ am Graph): Auslastung in % von Bad Pyrmont, Goslar
  und Weser-Ems in einem Graph – Ist durchgezogen, Prognose gestrichelt, feste Standortfarben, Linien bei 70/85/100 %,
  Tooltip mit allen drei Standorten (Prozent und Plätze). Prozent macht unterschiedlich große Standorte vergleichbar.
* Feinschliff: Tooltips bleiben im Diagramm, Diagramme blenden beim Wechsel weich ein.

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
`backup/v6.28.0`, vor 0.2.0 `backup/modern-0.1.0`, vor 0.3.0 `backup/modern-0.2.0`, vor 0.4.0 `backup/modern-0.3.0`, vor 0.5.0 `backup/modern-0.4.0`, vor 0.6.0 `backup/modern-0.5.0`, vor 0.7.0 `backup/modern-0.6.0`, vor 0.8.0 `backup/modern-0.7.0`, vor 0.9.0 `backup/modern-0.8.0`, vor 0.10.0 `backup/modern-0.9.0`, vor 0.11.0 `backup/modern-0.10.0`, vor 0.12.0 `backup/modern-0.11.0`, vor 0.13.0 `backup/modern-0.12.0`, vor 0.14.0 `backup/modern-0.13.0`, vor 0.15.0 `backup/modern-0.14.0`, vor 0.16.0 `backup/modern-0.15.0`, vor 0.17.0 `backup/modern-0.16.0`, vor 0.18.0 `backup/modern-0.17.0`, vor 0.19.0 `backup/modern-0.18.0`, vor 0.20.0 `backup/modern-0.19.0`, vor 0.21.0 `backup/modern-0.20.0`, vor 0.22.0 `backup/modern-0.21.0`, vor 0.23.0 `backup/modern-0.22.0`, vor 0.24.0 `backup/modern-0.23.0`, vor 0.25.0 `backup/modern-0.24.0`, vor 0.26.0 `backup/modern-0.25.0`, vor 0.27.0 `backup/modern-0.26.0`, vor 0.28.0 `backup/modern-0.27.0`, vor 0.29.0 `backup/modern-0.28.0`, vor 0.30.0 `backup/modern-0.29.0`, vor 0.31.0 `backup/modern-0.30.0`, vor 0.32.0 `backup/modern-0.31.0`, vor 0.33.0 `backup/modern-0.32.0`, vor 0.33.1 `backup/modern-0.33.0`, vor 0.33.2 `backup/modern-0.33.1`, vor 0.34.0 `backup/modern-0.33.2`, vor 0.35.0 `backup/modern-0.34.0`, vor 0.36.0 `backup/modern-0.35.0`, vor 0.37.0 `backup/modern-0.36.0`, vor 0.37.1 `backup/modern-0.37.0`, vor 0.38.0 `backup/modern-0.37.1`, vor 0.38.1 `backup/modern-0.38.0`, vor 0.39.0 `backup/modern-0.38.1`, vor 0.40.0 `backup/modern-0.39.0`, vor 0.40.1 `backup/modern-0.40.0`, vor 0.41.0 `backup/modern-0.40.1`, vor 0.42.0 `backup/modern-0.41.0`, vor 0.43.0 `backup/modern-0.42.0`, vor 0.44.0 `backup/modern-0.43.0`, vor 0.44.1 `backup/modern-0.44.0`, vor 0.45.0 `backup/modern-0.44.1`, vor 0.46.0 `backup/modern-0.45.0`, vor 0.47.0 `backup/modern-0.46.0`, vor 0.48.0 `backup/modern-0.47.0`, vor 0.49.0 `backup/modern-0.48.0`, vor 0.50.0 `backup/modern-0.49.0`, vor 0.51.0 `backup/modern-0.50.0`, vor 0.52.0 `backup/modern-0.51.0`, vor 0.53.0 `backup/modern-0.52.0`, vor 0.54.0 `backup/modern-0.53.0`, vor 0.55.0 `backup/modern-0.54.0`, vor 0.56.0 `backup/modern-0.55.0`, vor 0.57.0 `backup/modern-0.56.0`, vor 0.58.0 `backup/modern-0.57.0`, vor 0.59.0 `backup/modern-0.58.0`, vor 0.60.0 `backup/modern-0.59.0`, vor 0.61.0 `backup/modern-0.60.0`, vor 0.62.0 `backup/modern-0.61.0` (jeweils auch als Zip in `Sicherung`).
