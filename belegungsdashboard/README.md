# Belegungsdashboard 6.3

Desktop-Dashboard für die Internatsbelegung der INN-tegrativ gGmbH (Bad Pyrmont, Goslar,
Weser-Ems): Lage heute, Verlauf, Prognose mit ehrlicher Unsicherheit, Listen-Import und ein
Chat-Assistent, der jede Zahl direkt aus den Daten berechnet.

## Start

**Windows, einfachster Weg:** Doppelklick auf `Start.bat`. Beim ersten Start wird eine eigene
Python-Umgebung im Ordner `.venv` angelegt und alles installiert (einmalig, einige Minuten;
Voraussetzung: Python 3.11+ von python.org). Danach startet das Dashboard direkt.
`pivot_neu.xlsx` in diesen Ordner legen oder beim Start auswählen.

Von Hand:

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

## Neu in 6.16 – Neuigkeiten, Mängel, eigene Symbole

* **Glocke oben rechts + Leiste „Neuigkeiten“:** Was im Hintergrund passiert (Gebäudeplan oder UWT automatisch
  übernommen, Erinnerung fällig, Reinigung offen vor Anreise, Facility-Check …), steht jetzt nur noch hier – keine
  Einblendungen mehr zwischendurch. Die Glocke zählt die ungelesenen; Klick blendet die Leiste ein/aus. Ein Klick auf
  eine Neuigkeit führt hin; ✓ = alle gelesen, ✕ = entfernen. Im breiten Fenster steht die Leiste neben dem Inhalt,
  im schmalen schwebt sie darüber. Kurze Einblendungen gibt es nur noch als Antwort auf eigene Klicks
  (gespeichert + Rückgängig, Fehler).
* **Mängel je Zimmer:** In der Zimmerkarte unter „Zustand“ Vorschläge zum Antippen – Teppich/Boden beschädigt oder
  verschmutzt, Wand, Schimmel, Fenster, Heizung, Bad, Abfluss, Wasserhahn, Licht/Steckdose, Möbel, Matratze,
  Tür/Schloss, Rauchmelder, Geruch, Ungeziefer, Grundreinigung, Sonstiges. Antippen = offen seit heute, nochmal
  antippen = behoben (bleibt mit Datum im Verlauf).
  * Zimmerplan → Zimmer: Chip **„Mängel“** (bzw. unter „Filter“ → Mangel einzeln); Karten zeigen die Mängel rot,
    Kacheln ein ⚠.
  * „Drucken“ → **Mängelliste für das FM** (Drucken, PDF) oder **kopieren für eine Mail**.
  * Start → Heute: „N Zimmer mit offenen Mängeln“ (zur Info).
* **Eigene Symbole:** Renoviert = Farbrolle, Mängel = Werkzeug (Optimieren behält den Funken).

## Neu in 6.15 – Zimmer finden

* **Reiter bleiben stehen:** Im Zimmerplan (und unter Daten & Import) scrollen Reiter und Kennzahlen nicht mehr mit.
* **Reiter „Zimmer“ = Zimmer finden** (ersetzt „Häuser“ und die Zimmerliste):
  * eine Suchleiste (Zimmer, Name, Notiz) und ein Tag, an dem Status und Bewohner gelten,
  * Chips zum An-/Ausschalten: **Status** (Frei · Belegt · Geplant · Gesperrt, mit Anzahl), **Haus** (2 · 3.1 · 3.2 ·
    3.3 · 6) und **Eigenschaften** mit Symbolen: ✦ Renoviert · Vinyl · Teppich · Tier · Doppel,
  * Seltenes unter **„Filter“**: andere Böden, „renoviert seit …“, Bad über den Flur, Gästezimmer, Personengruppe,
    Zimmer außer Betrieb; **„Zurücksetzen“** erscheint, sobald etwas gefiltert ist,
  * drei Ansichten zum Umschalten: **Übersicht** (Kacheln wie bisher „Häuser“), **Karten** (je Etage eine Spalte, je
    Zimmer Status, Bewohner, Maßnahme, Zeitraum – wie der Gebäudeplan im Belegungssystem) und **Liste** (Tabelle),
  * oben die Kennzahlen der Auswahl (Zimmer · belegt · frei · Auslastung) und **„Drucken“** (Zimmerliste, PDF,
    Kopieren für Excel, Belegung als Excel). In der Liste zusätzlich „Bearbeiten“ (Renovierung/Boden setzen).
* **Stammdaten** sind jetzt ein eigener Reiter (bisher unter „Zimmer“).
* **Zuteilen:** „Drucken“ steht rechts direkt neben „Übernehmen“ (bisher „Export“ links).
* **Renovierungsliste ergänzt:** 23 weitere Zeilen (u. a. Haus 2, 3.–5. OG; Haus 3.1/3.2/3.3/6 aus 2018/2019) –
  renoviert, Boden **Vinyl (vermutet)**; ein schon sicher eingetragener Boden bleibt. 6 Zeilen gibt es im
  Gebäudeplan nicht (6-101, 6-204, 6-205, 6-208, 3.1-214, 3.1-220).

## Neu in 6.14 – ruhiger, nach Aufgaben geordnet

* **Start „Heute“:** eine ruhige Liste der Vorgänge statt sieben gleich lauter Kacheln, gegliedert in **Zuerst
  klären** (Konflikte, Einzug ohne Reinigung, Anreisen in ≤ 3 Tagen ohne Zimmer …), **Als Nächstes** (Anreisen
  ohne Zimmer, Buchungen eintragen, Posteingang, Erinnerungen …) und **Zur Info** (eingeklappt). Jede Zeile hat
  genau eine Aktion, die direkt dorthin führt, wo der Vorgang bearbeitet wird („Zuteilen“, „Eintragen“, „Lösen …“).
  Erinnerungen lassen sich mit ✓ direkt abhaken. Die Kacheln gibt es weiter unter „Übersicht“.
* **Ein Ort für alle Importe:** Der Zimmerplan-Reiter „Quellen“ entfällt. Gebäudeplan, ZKL und Zimmer-Pivot stehen
  unter **Daten & Import → „Gebäudeplan & ZKL“**, neben Anreisen und UWT. Die Statistik-Daten (Pivot & Kapazitäten,
  Mieten, Manuelle Einträge) stehen rechts davon, abgetrennt.
* **Puffer und Facility-Check** stehen jetzt unter **Einstellungen → Zimmerplanung**.
* **Verlauf:** Das Änderungsprotokoll öffnet sich im Zimmerplan unter **„Mehr“ → „Verlauf“**, dort auch mit
  „Letzte Änderung rückgängig“. Ebenfalls unter „Mehr“: neues Fenster, Importe, Einstellungen.
* **Seitenleiste nach Aufgaben:** Arbeiten (Zimmerplan, Posteingang, Termine) · Auswerten · Verwalten.
* **Zuteilen:** sichtbar sind nur noch „Export“ und „Übernehmen“. Person hinzufügen, neu vorschlagen und Zurücknehmen
  liegen unter „Mehr“.
* **„Zimmer wechseln“ überall gleich:** Ob aus dem Zeitstrahl (ziehen oder Rechtsklick) oder aus der Personenkarte –
  derselbe Ablauf mit Regeln, DZ-Partner-Frage, „vorher → nachher“, Prüfung gegen den aktuellen Stand und
  Rückgängig. Wer schon eingezogen ist, zieht über „Zimmer wechseln (Umzug ab …)“ um.
* Analyse und Konzept: `UX_KONZEPT.md`, Teil 2.

## Neu in 6.13 – Änderungen sicher und nachvollziehbar

* **Vorschau vor dem Speichern:** Würde eine Aktion mehr ändern als die gewählte Person, zeigt ein Fenster vorher
  „alt → neu“, und zwar je Person. Das betrifft:
  * Zuteilen → Übernehmen (z. B. nach „Neu“ werden schon gespeicherte Zimmer anders, „fest“ entfällt, jemand
    verliert sein Zimmer)
  * Konflikte lösen (inkl. DZ-Partner, die mitziehen)

  Grau steht, was dadurch zusätzlich passiert. Rot steht, was erst gelöst werden muss: Das Zimmer ist inzwischen
  belegt oder wurde in einem anderen Fenster geändert. Dann wird nichts gespeichert. Nur neue Planungen gehen wie
  bisher ohne Rückfrage.
* **Rückgängig:** Nach jeder Zimmer-Änderung erscheint unten rechts die Meldung mit dem Knopf **„Rückgängig“**,
  alternativ **Strg+Z**. Das gilt für Zuteilen, Verschieben, Umzug, „fest“, Zurücknehmen und Konflikte. Wurde
  danach schon etwas anderes gespeichert, lehnt das Programm ab, statt fremde Änderungen zu überschreiben.
* **Nie doppelt belegen:** Ein Zimmer, das im Zeitraum belegt oder gesperrt ist, kann auch von Hand nicht mehr
  vergeben werden. Das gilt für Personenkarte, Personendialog und Posteingang. Ausnahmen gegen Regeln (z. B.
  Gästezimmer) gehen weiterhin.
* **Kein halber Stand:** Bricht das Speichern ab (z. B. Netzlaufwerk weg), bleibt der Stand davor. Das
  Änderungsprotokoll zeigt nur, was wirklich gespeichert wurde.
* **Klarere Rückfragen:**
  * „Planung entfernen“ fragt nach.
  * Beim Zimmerwechsel einer „festen“ Planung steht dabei, dass sie wieder „geplant“ wird.
  * Umzug zurücknehmen nennt bei einem Tausch den Gegen-Umzug.
* **Reiter im Zimmerplan nach Aufgaben geordnet:** Planen (Zuteilen · Zeitstrahl · Häuser) | Erledigen (Aufgaben ·
  Abreisen · Reinigung) | Verwalten (Zimmer · Quellen). Jeder Reiter erklärt im Tooltip, wofür er da ist.
* Analyse und Konzept: `UX_KONZEPT.md`.

## Neu in 6.12

* **Frei nach Planung:** Wie viele Zimmer sind noch frei, wenn alle Anreisen ein Zimmer haben – auch die noch ohne
  Zimmer (probeweise nach den Regeln zugeteilt, nichts wird gespeichert).
  * Zimmerplan-Kopf: „nach Planung mind. N frei · KW …“ (Maus darüber: alle 12 Wochen, jetzt ↔ nach Planung).
  * Aufgaben → Engpässe: Spalten „Frei jetzt“ und „Frei nach Planung“; EMR, Doppel und Ampel nach Planung.
  * Startseiten-Kachel „Engpässe“ zeigt die Werte nach Planung.
* **Haus 6, 4. OG:** alle Zimmer renoviert (Datum unbekannt, wo keins bekannt ist), Boden Vinyl (sicher).
  Renovierungslisten können jetzt „ja“ statt eines Datums und einen Boden je Zeile enthalten.

## Neu in 6.11

* **Renovierung und Boden je Zimmer:** neue Zimmer-Eigenschaften „renoviert am“ und „Boden“ (mit Merker „vermutet“).
  Die mitgelieferte Renovierungsliste (`Renovierungen_Import.tsv` im Programmordner, 77 Zimmer) wird beim ersten
  Start einmal übernommen – Boden „Vinyl (vermutet)“. Ein sicher eingetragener Boden wird nie überschrieben.
* **Zimmerliste** (Zimmerplan → Reiter „Zimmer“, oben): filtern nach Haus, Renovierung (renoviert, nicht
  renoviert, seit Jahr), Boden, Tier-/Doppel-/Gästezimmer, Bad über den Flur, heute frei, Suche. Sortierbar,
  **Drucken/PDF** (Querformat, mit/ohne Bewohner) und **Kopieren** für Excel. Zeilen markieren →
  **„Eigenschaften setzen …“** (Renovierung/Boden für mehrere Zimmer); **„Renovierungen einfügen …“** für weitere
  Listen aus Excel (Haus, Zimmer, Notiz, Datum). Kennt der Zimmerplan den Boden nicht, steht der Boden laut ZKL da.
* Zimmerkarte zeigt „renoviert … · Boden …“.

## Neu in 6.10

* **Abreiseliste** – Zimmerplan → Reiter **„Abreisen“** (auch von der Startseiten-Kachel „Abreisen“ → „Abreiseliste
  öffnen“): Heute, Morgen, Diese Woche, Nächste Woche, 14 Tage, Monat oder frei von–bis. Je Abreise Tag, Zimmer, Name,
  Maßnahme und die **nächste Anreise ins Zimmer** (bis dahin muss es fertig sein). Umzüge zählen nicht als Abreise.
  **Drucken/PDF** je Tag nach Haus und Zimmer mit Spalten zum Abhaken (Schlüssel, Abnahme) und Notiz; **Kopieren** für
  Excel; Doppelklick öffnet die Zimmer-/Personenkarte.
* **Zimmer sortieren nach Haus → Etage → Nummer** (2 … 3.1 UG, EG, 1. OG … 3.2 … 6), „– nicht zugeteilt –“ zuletzt –
  in allen Tabellen, auch in Spalten mit Auswahlliste (Zuteilen → Zimmer).
* Reiterleiste im Zimmerplan wird bei schmalem Fenster kompakter (kein waagrechtes Scrollen bei 1000 px).

## Neu in 6.9.1

* Sortieren auch in Spalten mit Auswahllisten, Häkchen oder Pillen (z. B. Zuteilen → „Zimmer“) – nach dem aktuell
  gewählten Wert, auch wenn er nach dem Laden geändert wurde.

## Neu in 6.9

* **Je Kurs ein Flur:** Beim Zuteilen bildet jeder Kurs (z. B. „GS VW 2606“) eine eigene Gruppe – vorher kamen
  alle Reha-Kurse eines Anreisetages in eine Gruppe. Personen mit Tier bleiben außen vor (Haus 3.1).
* **Kurs zusammenführen** (Belegung optimieren): Zwei Bewohner aus verschiedenen Kursen tauschen die Zimmer, wenn
  danach beide mindestens so viele aus ihrem Kurs auf dem Flur haben und es zusammen mehr sind. Nur Einzelzimmer,
  keine Tier-Zimmer, nur wer noch mindestens 60 Tage bleibt; alle Regeln gelten. Nicht vorausgewählt – abhaken,
  oben den **Umzugstag für Tausche** wählen, übernehmen. Jeder Tausch wird als zwei verbundene Umzüge angelegt
  (gemeinsam abschließen bzw. zurücknehmen) und steht bis zum Abschließen unter Aufgaben → Eintragen.
* Mit der Datenkopie vom 14.10.: 36 Tausche (72 Umzüge) heben den Anteil „wohnt auf dem Haupt-Flur seines Kurses“
  von 34 % auf 69 % (Kurse ganz auf einem Flur: 1 → 9). Danach je Auszugswelle einige weitere Tausche.

## Neu in 6.8

* **Tabellen sortieren:** Klick auf eine Spaltenüberschrift sortiert aufsteigend, ein zweiter Klick absteigend (Pfeil
  in der Überschrift). Zimmer werden „natürlich“ sortiert (2-9 vor 2-10), Daten (TT.MM.JJJJ) als Datum, Zahlen als
  Zahl, Namen ohne Rücksicht auf Groß/Klein. Die Sortierung bleibt beim Aktualisieren erhalten; Doppelklick, Auswahl
  und Knöpfe treffen weiterhin die richtige Zeile. Gilt für alle Tabellen (Zimmerplan, Termine, Suche, Inventar,
  Posteingang, Daten, Einstellungen …).

## Neu in 6.7.1

* Begriff: **„Planung abschließen (fest)“** statt „als belegt markieren“ – im Rechtsklick-Menü des Zeitstrahls, in der
  Personenkarte und im Umzug-Dialog („Umzug abschließen (fest)“). Zurück mit „Wieder auf geplant“.
* Lädt eine Zimmerkarte nach einer Änderung nicht neu, erscheint jetzt eine Fehlermeldung (vorher blieb sie still).

## Neu in 6.7

* **Von geplant auf belegt wechseln – der Zimmerplan als Hauptwerkzeug.** Ohne neuen Gebäudeplan:
  * Geplante Person: Rechtsklick im Zeitstrahl bzw. Zimmer-/Personenkarte → „Planung abschließen (fest)“. Zurück
    geht es mit „Wieder auf geplant“.
  * Umzug: im Umzug-Dialog „Umzug steht fest bzw. ist erfolgt – Planung abschließen (fest)“ (bei Umzug heute oder früher
    vorausgewählt), später umschaltbar in der Karte und im Rechtsklick-Menü.
  * Belegt heißt: im Zeitstrahl türkis, keine Aufgabe unter „Eintragen“, kein Hinweis „fehlt im Gebäudeplan“.
  * Ein **älterer** Gebäudeplan ändert daran nichts. Ein **neuerer** Gebäudeplan (Stand nach dem Markieren) gilt
    wieder, so bleiben Belegungssystem und Zimmerplan auf demselben Stand, sobald ihr importiert.
* **ZKL einmalig abgleichen:** Im Abgleich sind „bewohnt, im Gebäudeplan frei“, „nicht belegbar“ und „Tier-Pool“
  vorausgewählt; „Gästehaus (SGH)“ nicht.

## Neu in 6.6

* **Zimmerkontrollliste (ZKL) als Import** – Zimmerplan → Quellen → „ZKL importieren“ (Excel). Der Gebäudeplan bleibt
  die Grundlage; die ZKL wird **abgeglichen**:
  * Automatisch übernommen: **Tier** (Kundengruppe „Reha-Tier“ – zählt für die Regel Haus 3.1 UG), **TN-Nummer** der
    Bewohner (Posteingang findet sie über die TN-Nr.) und Zimmer-Infos (Boden, Reno, Hinweise) in der Zimmerkarte.
  * Zum Entscheiden im Dialog „Abgleich anzeigen“: laut ZKL bewohnt, im Gebäudeplan frei (→ als belegt übernehmen);
    laut ZKL Lager/Büro/Appartment/Musterzimmer (→ gehört nicht zum Internat); laut ZKL Gästehaus (SGH) bzw.
    Tier-Pool anders als im Zimmerplan; Person inzwischen in einem anderen Zimmer (nur Info).
  * Angehakt wird übernommen, der Rest als geprüft abgelegt („Auch geprüfte zeigen“ holt alles wieder).
  * Bei mehreren Zimmerblättern gilt das mit den neuesten Daten. „3.3-1xx“ der ZKL wird Haus 3.2 zugeordnet, wo es
    die Nummer nur dort gibt.

## Neu in 6.5

* **Haus 3.1 Untergeschoss nur mit Tier:** Ohne Tier teilt das Programm dort nie automatisch zu – auch nicht,
  wenn sonst nichts frei ist. Von Hand geht es weiterhin: In der Zimmerauswahl steht es unter dem Strich als
  „Ausnahme: nur mit Tier“, der Vorschlag trägt dann die Warnung „Regel verletzt“.
* **Dieselbe Anreise auf einen Flur:** Beim Zuteilen kommt eine Anreise-Gruppe (gleicher Tag, gleiche Maßnahme)
  wie bisher zuerst auf den Flur, auf dem alle Platz haben, sonst auf möglichst wenige Flure derselben Etage.
  Neu: **Belegung optimieren** zählt das ebenfalls. Je Person derselben Anreise auf dem Flur gibt es Punkte,
  daher schlägt es Umzüge und Tausche (auch zwischen RVL und RVT) vor, die Gruppen zusammenführen. Personen mit
  Tier bleiben außen vor (sie wohnen in Haus 3.1), UWT-Klassen plant „UWT neu zuteilen“.
* Grenze: Zusammenrücken geht nur, wo Zimmer frei werden. Wer schon wohnt, wird nicht automatisch verschoben.

## Neu in 6.4

* **Umzug für Eingezogene:** Auch wer schon im Zimmer wohnt (laut Gebäudeplan oder schon angereist), kann ab
  einem Tag in ein anderes Zimmer wechseln.
  * Im **Zeitstrahl** den Balken in die Zeile des neuen Zimmers ziehen. Der Tag, an dem du loslässt, ist der
    Umzugstag (Vorschlag, im Dialog änderbar).
  * Oder **Rechtsklick** auf den Balken → „Umzug in ein anderes Zimmer …“. Dort auch „Person öffnen“, „Umzug
    ändern“ und „Umzug zurücknehmen“.
  * Oder in der **Zimmer-/Personenkarte** (Klick aufs Zimmer) der Knopf „Umzug in ein anderes Zimmer …“.
  * Der Dialog zeigt nur Zimmer, die ab dem Umzugstag bis zur Abreise frei sind – oben die zulässigen, darunter
    Ausnahmen mit Grund. Doppelzimmer bleiben UWT und Gästen vorbehalten.
  * Das alte Zimmer endet am Umzugstag (Auszugsreinigung) und ist danach frei. Das neue steht ab dem Umzugstag als
    geplant im Zeitstrahl („↪ … aus 2-111“) und unter **Aufgaben → Eintragen** („Umzug aus …“), bis es im
    Belegungssystem umgebucht ist. Zeigt der nächste Gebäudeplan die Person im neuen Zimmer, gilt der Umzug als
    erledigt.
  * Geplante Personen, die noch nicht angereist sind, werden wie bisher ganz verschoben (ohne Umzugstag).

## Neu in 6.3

* **Posteingang** (Seitenleiste): Mails zu **Gästehaus-Reservierungen, Anmeldungen, Stornos, Abbrüchen und
  Hinweisen** einfügen (in Outlook Strg+A, Strg+C – hier Strg+V), als .eml hineinziehen oder mit „Aus Outlook“
  die markierten Mails holen. Das Programm erkennt Art, Name, TN-Nr., Zeitraum („14. – 15.10.“, „27.01. bis
  29.01.2027 (2 ÜN)“, „letzter Tag …“, „Ende: …“), Abbruchgrund und Wiederaufnahme – Grußformel und
  Unterschrift werden ignoriert. Es sucht die Person (TN-Nr. vor Name) und schlägt Schritte vor:
  * Gästehaus/Anmeldung: Person anlegen und **Zimmer reservieren** (Gäste → Gästezimmer; Zimmer änderbar),
    Wiedervorlagen „Bestätigung senden“ und „Kostenübernahme eingegangen?“.
  * Storno: Planung entfernen (Zimmer wird frei), Person entfernen bzw. „ohne Internat“; steht die Buchung im
    Belegungssystem, eine Aufgabe dafür.
  * Abbruch: Abreise auf den letzten Tag setzen, Notiz (Grund, Wiederaufnahme, Zimmer geräumt) und **Prüfliste**
    (Belegungssystem geändert, Zimmer abgenommen, Schlüssel zurück, Endreinigung) – bleibt „zu prüfen“, bis alles
    abgehakt ist.
  * Hinweis: Notiz an der Person, mit Wiedervorlage zwei Tage vor der Anreise.
  Nichts passiert ohne „Umsetzen“; alles ist vorher änderbar. Abgelegte Mails stehen unter „Eingänge“,
  die Seitenleiste zeigt, wie viele offen sind. Die Mails liegen nur lokal (`importe/posteingang.json`).
* **Belegung optimieren** (Zimmerplan → „Optimieren“ oder Kachel auf der Startseite): prüft alle Belegungen wie
  beim Zuteilen und schlägt mit Begründung vor: **Regelverstöße** (z. B. lange Maßnahme auf Haus 2, 1. OG,
  Reha in Haus 6) mit freiem Ersatz, **bessere Zimmer** und **Tausche** für geplante Personen. Buchungen aus dem
  Belegungssystem bucht das Programm nicht selbst um, sondern legt eine Aufgabe an. DZ-Paare und UWT-Klassen
  bleiben zusammen; schon eingetragene Buchungen werden nur bei großem Gewinn und nicht vorausgewählt vorgeschlagen.
* **Startseite:** Titel und Untertitel im Anpassen-Modus änderbar; neue Kacheln „Posteingang“ und
  „Belegung optimieren“.
* **Engpässe** klar definiert: Erklärung in Kachel und Aufgaben, jede Zahl einzeln eingefärbt, Kalenderwochen
  mit Datum („KW 42 · 12.10.–18.10.“), Grenzen für knapp/kritisch unter Aufgaben → Engpässe → „Grenzen …“.

## Neu in 6.2

* **Name änderbar:** Einstellungen → „Name des Dashboards“ – Name und Zusatzzeile (z. B. „Internat Goslar“)
  stehen in der Seitenleiste, im Fenstertitel und im Infobereich. „Zurücksetzen“ stellt „Belegung“ wieder her.
* **Design wählbar:** Einstellungen → Erscheinungsbild → Design: **Klassisch** (bisheriges Aussehen, Standard),
  **Modern** (Indigo, dunkle Seitenleiste, größere Rundungen und Titel), **Kompakt** (kleinere Schrift und
  Abstände – mehr auf einen Blick), **Warm** (Sandtöne, grüne Seitenleiste, weich). Jedes Design gibt es hell
  und dunkel; Hochkontrast bleibt unverändert. Umschalten wirkt sofort, ohne Neustart.

## Neu in 6.1

Rückweg zu älteren Ständen: siehe **ROLLBACK.md**.

* **Startseite „Mein Dashboard“** (erster Eintrag in der Seitenleiste): Kacheln mit dem, was heute zu tun ist –
  Zimmer heute, Jetzt erinnern (mit „Erledigt“), Anreisen der nächsten 7 Tage (Klick → Zuteilen), Abreisen,
  Reinigung, Im Belegungssystem eintragen, Engpässe, Facility-Check, Neueste Notizen, Belegung je Standort,
  Schnellzugriff. **„Anpassen“** oben rechts: Kacheln an „⠿ ziehen“ auf eine andere Kachel ziehen
  (wird davor eingesetzt), „Breiter/Schmaler“, × entfernt, „Kachel hinzufügen“, „Standard“. Wird gespeichert.
* **Tabs** (Leiste ganz oben, wie im Browser): Jeder Tab merkt sich seine Ansicht – Seite und Unterreiter,
  im Zimmerplan auch Haus, Suche und Monat des Zeitstrahls. Seitenleiste wechselt die Seite im aktuellen Tab;
  **Strg+Klick**, mittlere Maustaste oder Rechtsklick → „In neuem Tab öffnen“; „+“ dupliziert die Ansicht
  oder öffnet eine Seite; Strg+T neu, Strg+W schließen, Strg+Tab wechseln; Tabs lassen sich verschieben
  und sind beim nächsten Start wieder da.
* **Kalender:** Die Datumsauswahl ist neu gebaut – vorher zeigten die Tage „…“ (die Kalenderzellen erbten die
  Tabellen-Abstände). Heute umrandet, Auswahl gefüllt, Monat per Pfeil, Mausrad oder Bild-Tasten, „Heute“.
* **Minimiert sparsam:** Solange das Dashboard minimiert oder im Infobereich ist, wird nichts neu berechnet oder
  gezeichnet (vorher bei jeder Änderung alles); beim Zurückholen genau einmal. Beim Minimieren werden
  Zwischenspeicher geleert und unter Windows ungenutzter Arbeitsspeicher abgegeben. Erinnerungen kommen weiter.
* **Schmale Fenster:** Bei 1000 px Breite keine waagerechte Bildlaufleiste mehr auf allen Seiten
  (Seitenuntertitel kürzt mit „…“, Zeitraum- und Filterzeilen brechen um).

## Neu in 6.0 (Oberfläche überarbeitet)

Rückweg zur Version 5.17.0: siehe **ROLLBACK.md**. Die Datenformate sind unverändert – 5.17.0 läuft mit
denselben Daten weiter.

* **Zimmer- und Personenkarte:** Klick auf ein Zimmer (Häuser, Zeitstrahl), „Öffnen“ in der Suche oder
  „Öffnen“ bei einer Wiedervorlage zeigt eine Karte in einem eigenen Fenster – mehrere gleichzeitig möglich:
  * **Bewohner** (heute und kommende, jeweils anklickbar): Zimmer ändern (wenn hier geplant), Abreise,
    Notizen mit Wiedervorlage, „Alle Angaben …“ (Geschlecht, Tier, Gruppe, Bemerkung, Erinnerung).
    Wer nur im Gebäudeplan steht, ist im Belegungssystem gebucht – Zimmer/Abreise dort ändern,
    Notizen und Wiedervorlagen gehen trotzdem.
  * **Zum Zimmer:** dauerhafter Hinweis (z. B. „bodentiefe Dusche“), Notizen mit Wiedervorlage
    (z. B. „Heizung defekt – Hausmeister“), Ausstattung aus dem Inventar.
  * Darunter Zeitstrahl und alle Belegungen.
* **Suche:** „Öffnen“ geht jetzt für alle Treffer – auch für Bewohner aus dem Gebäudeplan und UWT
  (vorher war „Person öffnen“ dort gesperrt). „Im Zeitstrahl“ springt zum Zimmer im Zeitstrahl.
* **Mehrere Ansichten gleichzeitig:** Zimmerplan → „Neues Fenster“ (oben rechts) öffnet den aktuellen Reiter
  zusätzlich als eigenes Fenster, z. B. Zeitstrahl neben Zuteilen. Was in einem Fenster gespeichert wird,
  erscheint sofort in allen anderen.
* **Mehr Platz im Zimmerplan:** Info-Hinweise (Gebäudeplan-Alter, EMR-Zimmer, UWT-Liste) stecken hinter
  „n Hinweise“ in der Kennzahlenzeile; Warnungen und Konflikte bleiben immer sichtbar.
  Zuteilen: „Übernehmen“ steht rechts neben den Aktionen.
* **Datensicherung:** Beim Start einmal am Tag und vor jedem Update werden alle Arbeitsdaten
  (Zuweisungen, Termine, Notizen, Importe, Einstellungen) nach `Sicherungen/` kopiert (die neuesten 30 bleiben).
  Einstellungen → Datensicherung: Liste, „Jetzt sichern“, „Wiederherstellen …“ (der aktuelle Stand wird
  vorher gesichert), „Ordner öffnen“.

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
* Ohne Abreise zählt eine Person nur als Termin – oder mit einer einstellbaren Standarddauer;
  EMR reisen immer **einen Tag vor** dem Datum der Anreiseliste an (Liste Montag → Sonntag da)
  und **mittwochs** ab. Die Abreise wird automatisch eingetragen (Anzeige „14.10.2026 (EMR)“) und
  lässt sich per Stift ändern oder löschen – von Hand Geändertes bleibt erhalten.

### UWT (neu)

Unter **Daten & Import → UWT** eine dieser Dateien hochladen:

* **Blockbeschulungsplan der BBS (PDF, ganzes Schuljahr)** – Klassen als Spalten, Schulwochen
  als Zeichen. Zusammenhängende Wochen einer Klasse bilden einen Block (Montag bis Freitag der
  letzten Woche). Die Anzahl kommt aus den **Klassenstärken im Internat**, die im Import-Dialog
  stehen und gespeichert werden (Stand: CUA26 15, CUA25 10, CUA24 16, CUW26 11, CUW25 9,
  CUW24 16, CUK26 8, CUK25 9, CUK24 9). Klassen mit 0 (z. B. Chemikanten CCK) zählen nicht.
* **Anreisekalender (Excel)** – Farbe je Klasse, Zahl = Anzahl, Legende Farbe → Klasse.
* **An- und Abreiseliste eines Blocks (PDF)** – mit Personen und Zimmern.

Die Klasse bleibt über das Wochenende im Haus, die Zimmer bleiben bis Blockende belegt. Ein
Block ersetzt einen vorhandenen Block derselben Klasse, mit dem er sich überschneidet –
Personen und Zimmer aus einer PDF-Liste bleiben dabei erhalten. Die UWT steht nicht in der
Pivot und zählt über den ganzen Block zur Belegung Goslar (Kategorie UWT).

**Ordner `UWT`:** PDF- oder Excel-Dateien dort ablegen – beim Programmstart bzw. Öffnen des
Zimmerplans werden neue oder geänderte Dateien automatisch übernommen. Der Blockbeschulungsplan
2026/2027 liegt schon darin (u. a. 28.09.–09.10. CUA26/CUK25, 26.10.–06.11. CUW26/CUW24,
09.11.–20.11. CUK26/CUA25/CUK24, 23.11.–04.12. CUA26/CUW25, 07.12.–18.12. CUW26/CUK25/CUA24).
Die UWT wohnt immer in Haus 3.2, 3.3 oder 6.

**Klassenübersicht und Doppelzimmer:** Die Klassenübersicht (Excel, ein Blatt je Klasse mit ID, Name,
Vorname, „DZ Partner“) liegt ebenfalls im Ordner `UWT` (ohne Fotos und Geburtsdaten) und wird automatisch
übernommen; neue Fassung einfach dazulegen oder unter Daten & Import → UWT hochladen.

* Alle Blöcke einer Klasse bekommen die Namen aus der Übersicht (statt „Platz 1 …“), die Klassenstärke
  ist die Zahl der Teilnehmenden; alles unter „STORNO“ zählt nicht.
* **Gleiche DZ-Nummer = gemeinsames Doppelzimmer.** In ein solches Zimmer kommt niemand anderes; wer „-“
  oder nichts eingetragen hat (in einer Klasse mit DZ-Liste), wohnt allein, bevorzugt im Einzelzimmer.
  Klassen ohne DZ-Liste (z. B. CUA25, CUA26) teilen sich wie bisher Doppelzimmer innerhalb der Klasse.
* Klassen mit DZ-Liste werden zuerst geplant; Paare bekommen ein freies Doppelzimmer, notfalls auf einem
  anderen Flur. Geht es nicht, steht „DZ-Partner … in anderem Zimmer“ bei der Person.
* Hinweise der Übersicht (z. B. drei Personen mit derselben DZ-Nummer) stehen oben im Zimmerplan.
* **Automatisch zugeteilt:** Kommende UWT-Blöcke werden beim Öffnen des Zimmerplans gleich zugeteilt
  und gespeichert (laufende Blöcke nicht). Unter Zuteilen änderbar; wer dort von Hand entfernt wird,
  bekommt nicht wieder automatisch ein Zimmer. In der Zuteilung steht unter dem Namen „DZ: Partner“
  bzw. „allein“.

### Einheitsliste (alle Listen in einem Format)

Beliebige Listen (Anreiselisten, EMR-Listen, UWT-Listen, Klassenübersicht, handschriftliche
Doppelzimmerlisten, Mails …) lassen sich mit Claude in **ein** Format umbauen: Prompt in
`Vorlagen/Prompt_Einheitsliste.md`, Aufbau in `Vorlagen/Einheitsliste_Vorlage.xlsx`. Claude fragt
dabei immer nach dem **Enddatum**, wenn es nicht ersichtlich ist.

Spalten: Art (Anreise/UWT), Nachname, Vorname, TN-ID, Gruppe, Maßnahme, Klasse, Anreise, Abreise,
Internat, Geschlecht, Tier, DZ-Partner, Zimmer, Bemerkung, Quelle.

* Ergebnis (CSV oder Excel) in den Ordner `Listen` legen – beim Start übernommen – oder unter
  Daten & Import → Anreisen → „Anreiselisten hochladen“ wählen (mit Vorschau).
* Anreise-Zeilen wirken wie Anreiselisten (je Tag, EMR getrennt; die Datei ersetzt die Liste des
  Tages – darum immer alle Personen eines Tages aufführen). UWT-Zeilen werden Blöcke mit Namen,
  DZ-Partner gehen in die Klassenliste. Zeilen ohne Abreise werden gemeldet (UWT ohne Ende nicht
  übernommen).

### Zimmerplan Goslar (neu)

Eigene Seite **Zimmerplan** (Strg+5). Grundlage ist der **Gebäudeplan** als Word-Export
(.docx) aus dem Belegungssystem. Daraus kommen Zimmer, Betten, Belegungen mit Zeitraum,
Sperrungen/Renovierungen und Zimmerfreigaben („Frei teilw.“).

* **Automatisch:** Der Plan vom 03.10.2026 liegt schon im Ordner `Gebaeudeplan` und wird beim
  ersten Öffnen des Zimmerplans übernommen. Neue Pläne einfach in diesen Ordner legen (oder über
  „Gebäudeplan importieren“ wählen) – die neueste Datei wird automatisch übernommen, ein Plan mit
  älterem Stand ersetzt keinen neueren.
* **Word-Datei einfach aktualisieren:** Inhalt in der Word-Datei im Ordner `Gebaeudeplan` ersetzen und
  speichern – beim nächsten Öffnen des Zimmerplans wird sie übernommen (Stand = Speicherdatum).
* **Abgleich mit unserer Zuteilung:** Steht eine Person im Gebäudeplan (gleicher Name, Zeitraum
  überschneidet sich) – egal in welchem Zimmer –, gilt die Buchung dort und unsere Planung entfällt.
  Hinweise oben im Zimmerplan und in der Zuteilung: „anders gebucht als geplant“ (z. B. 2-109 statt
  2-201) und „Angereist? Im Gebäudeplan noch nicht gebucht“, wenn die Anreise vorbei ist und die Person
  im Gebäudeplan fehlt. Dieser Hinweis kommt nur, wenn der Gebäudeplan nach der Anreise erstellt wurde (ein
  älterer Plan kann die Person noch gar nicht enthalten) und die Buchung unter Aufgaben → „Im Belegungssystem
  eintragen“ noch nicht abgehakt ist.
* **Ohne Word:** Im Belegungssystem die Gebäudeansicht markieren (Strg+A), kopieren (Strg+C) und unter
  Zimmerplan → Quellen „Aus Zwischenablage einfügen“ klicken. Das Programm zeigt, wie viele Zimmer und
  Belegungen erkannt wurden, und übernimmt erst nach Bestätigung (Stand = heute).
* Die Zimmerliste (335 Zimmer) ist zusätzlich fest im Programm hinterlegt, ohne Namen – so kennt
  der Zimmerplan alle Zimmer auch ohne Import.
Die 17 Gästezimmer (Haus 2, Etage 6, 601–617) sind fest hinterlegt.

Die Seite hat sieben Reiter (Zuteilen, Aufgaben, Zeitstrahl, Häuser, Reinigung, Zimmer, Quellen):

* **Aufgaben** – der Arbeitsablauf nach dem Planen:
  * **Im Belegungssystem eintragen:** alles, was hier geplant ist, aber noch nicht im Gebäudeplan
    steht – je Anreisetag, zum Abhaken (nächste 2 Wochen / 8 Wochen / alle; „Kopieren“ liefert Zimmer,
    Name, Maßnahme, Zeitraum für Excel). Steht die Person im nächsten Gebäudeplan, verschwindet sie
    von selbst; wird das Zimmer geändert, ist der Haken wieder weg. Der Reiter zeigt die Zahl der
    offenen Einträge der nächsten 14 Tage.
  * **Facility-Check nach langem Aufenthalt:** Auszüge nach mindestens 6 Monaten (einstellbar unter Quellen →
    Planung) – „Elektrik prüfen, Fensterwartung“ zum Abhaken (4 Wochen zurück und voraus). 3 Tage vor so einem
    Auszug kommt einmal eine Windows-Meldung; in der Reinigungsliste steht „Facility-Check“ bzw. auf dem Ausdruck
    in der Notizspalte „Facility: Elektrik, Fenster“.
  * **Wochenblatt:** je Tag Zimmer, Abreise, Anreise und Reinigung – zum Aushängen (Drucken oder PDF,
    mit oder ohne Namen).
  * **Engpässe:** je Woche (12 Wochen) die ganz freien Zimmer gesamt, in den EMR-Etagen und die freien
    Doppelzimmer für die UWT – gelb/rot, wenn es knapp wird.
* **Zuteilen → Export:** **Anreiseliste** zum Ausdrucken (Name, Maßnahme, Zimmer, Anreise bis Abreise – nach
  Namen sortiert, mit Notizspalte), Excel-Liste, **Zimmerschilder** (ein Schild je Zimmer, Doppelzimmer mit beiden
  Namen) und **Schlüsselliste** (Ausgabe/Rückgabe zum Abzeichnen) der gewählten Anreise.
* **Quellen → Änderungsprotokoll:** wer wann wen geplant, umgeplant oder entfernt hat.

Weitere Reiter:

* **Zuteilen** – Anreisetag wählen (‹ › blättert), darunter der Vorschlag für alle Personen
  des Tages; „Person“ legt jemanden von Hand für diese Anreise an. Alle Gruppen eines Tages (z. B. drei UWT-Klassen) werden
  gemeinsam geplant, jede auf eigenen Fluren. Zimmer, Geschlecht und Tier je Person änderbar,
  dann „Übernehmen“ – übernommene Zuweisungen zählen bei späteren Vorschlägen als belegt.
  „Excel“ erzeugt Zimmerliste, Übersicht je Flur und freie Zimmer (druckfertig, A4 quer).
* **Zeitstrahl** – Zimmer als Zeilen, Tage als Spalten, Belegungen als Balken mit Namen
  (wie im Belegungssystem); Monat blättern, Haus wählen, nach Name/Zimmer suchen.
* **Häuser** – alle Zimmer je Haus/Etage/Flur an einem Tag; Filter Frei / Teilweise / Belegt /
  Geplant / Gesperrt mit Anzahl. Klick auf ein Zimmer öffnet die Zimmer- und Personenkarte (siehe „Neu in 6.0“).
* **Zimmer** – Stammdaten (siehe unten).
* **Häuser** – Filter nach Status (frei, belegt …) und nach **Personengruppen** (Mehrfachauswahl) (UWT, EMR, Assessment,
  RVL, RVT, Reha, Gäste, Mieter): „wohnt dort“ zeigt die Zimmer, in denen die Gruppe am gewählten
  Tag wohnt; „darf dort wohnen“ zeigt die laut Regeln erlaubten – mit „Frei“ kombiniert also, wo
  noch Platz für die Gruppe ist.
* **Zeitstrahl – Verschieben per Ziehen:** Geplante Zuweisungen (blau gestrichelt) mit der Maus in ein anderes
  Zimmer ziehen; nach der Rückfrage „verschieben?“ wird gespeichert (Änderungsprotokoll, Aufgaben → Eintragen).
  Belegte/gesperrte Zimmer oder fremde Mitbewohner lehnt das Programm ab, Regelabweichungen nennt die Rückfrage;
  DZ-Partner können mitziehen. Buchungen aus dem Gebäudeplan (türkis) lassen sich nicht ziehen.
* **Zeitstrahl** – Farben: belegt türkis, geplant blau gestrichelt, laut Zimmer-Pivot lila, gesperrt rot
  schraffiert. Die Legende ist zugleich Filter: „geplant“, „gesperrt“, „Pivot“ oder „belegt“
  anklicken (mehrere kombinierbar) zeigt nur Zimmer mit dieser Art, andere Balken blass. Gruppenfilter
  (Mehrfachauswahl) wie unter Häuser; bei „wohnt dort“ werden andere Gruppen blass gezeigt.
* **Frei gewordene Zimmer zuerst:** Vorschläge bevorzugen Zimmer, aus denen kurz vor der Anreise jemand
  auszieht (bis 4 Tage: stark, bis 10 Tage: etwas) oder in die kurz nach der Abreise wieder jemand einzieht.
  So fallen Aus- und Einzugsreinigung zusammen und lange freie Zimmer bleiben für lange Aufenthalte.
  Reserven (Tier-Zimmer, Doppelzimmer für UWT, EMR-Etagen) wiegen schwerer.
* **Reinigungstag:** Wenn möglich liegt zwischen Auszug und neuer Anreise ein ganzer Tag (Auszug Mi →
  Anreise ab Fr). Ist kein anderes Zimmer frei, wird trotzdem zugeteilt – mit dem Hinweis „Kein
  Reinigungstag“. Als feste Regel lässt sich der Abstand unter Quellen → „Puffer nach jeder Abreise“ setzen.
* **Reinigung** – Wochenliste (aus Gebäudeplan, übernommenen Zuteilungen und Zimmer-Pivot) als **eine Tabelle
  nach Frist**: **Zimmer · Auszug · Sauber bis spätestens**. **Samstags und sonntags wird nicht gereinigt:** die Frist
  ist der **letzte Werktag vor der nächsten Anreise** (Anreise Mo → Fr). Auszug Fr → Anreise Mo: „noch am
  Auszugstag“; Anreise am selben/nächsten Tag: „sofort nach Auszug“ (rot); kein Werktag dazwischen (Auszug Sa →
  Anreise Mo): „am Anreisetag vor der Anreise“ bzw. „Wochenende! Sonderreinigung“ (rot). Ohne Anreise danach
  „keine Anreise geplant“. Die Zimmervorschläge meiden Wechsel, bei denen kein Werktag zum Reinigen bleibt.
  Eine Zeile je Zimmerwechsel; Zimmer, die vorher leer standen, erscheinen mit „leer seit …“. Maus auf die
  Zeile zeigt, wer auszieht und wer kommt. Anreisen ohne übernommenes Zimmer werden als Hinweis gezeigt.
  * **Abhaken:** Jede Reinigung hat ein Häkchen (nochmal klicken = zurücknehmen). Ist ein Zimmer nicht
    abgehakt, obwohl heute/morgen jemand einzieht, gibt es einen roten Hinweis, eine Windows-Meldung und eine
    Zahl an „Zimmerplan“ in der Seitenleiste. Oben steht nur, was aus **früheren Wochen** noch offen ist – alles
    aus dieser Woche steht im jeweiligen Tag (keine doppelten Zeilen). Reinigungen vor dem ersten Start gelten
    als erledigt (lässt sich zurücknehmen). **Drucken**, **PDF** oder **Excel** mit Abhakkästchen und
    Notizspalte; Namen nur auf Wunsch („Namen auf der Liste“), sonst nur Maßnahme/Gruppe.
* **Quellen** – Gebäudeplan und Zimmer-Pivot importieren, Puffer nach Abreise.

Beim Hochladen von Anreiselisten lassen sich Gruppe (wenn die Maßnahme nicht erkennbar ist),
Geschlecht und Tier je Person direkt festlegen; danach bietet das Programm an, gleich zum
Zuteilungsvorschlag für die Anreise zu springen.

Feste Regeln:

| Gruppe | erlaubt |
|---|---|
| EMR | nur Haus 2, Etage 1–2 – Haus 2 Zimmer **101–110 ausschließlich EMR** (dort darf niemand sonst hin; EMR werden zuerst dort untergebracht) |
| Gäste | nur Gästezimmer Haus 2, Etage 6 (für andere nie vorgeschlagen) |
| Mieter | nur Haus 6 |
| UWT | Haus 3.2, 3.3 und 6 |
| RVL | bevorzugt Haus 3.1, sonst 3.2, 3.3 oder Haus 2 (nicht 1. OG) |
| Assessment, RVT, Reha-Maßnahmen | Haus 2 (Etage 1–5), 3.1, 3.2, 3.3 – nicht Haus 6 |

* **Doppelzimmer nur für UWT und Gäste – ohne Ausnahme:** andere Gruppen bekommen kein Doppelzimmer, auch nicht
  von Hand oder per Verschieben im Zeitstrahl. Ältere Planungen im Doppelzimmer erscheinen vor der Anreise als
  Konflikt („Neu planen“).
* **Tiere:** immer zuerst Haus 3.1 Untergeschoss, erst wenn dort nichts frei ist das Erdgeschoss.
* **Haus 2, 1. OG (Zimmer 101–124) nur für Kurzmaßnahmen** (EMR, Assessment, Aufenthalte bis 8 Wochen) –
  RVL, RVT und andere lange Aufenthalte kommen auf die anderen Etagen (von Hand als Ausnahme „nur Kurzmaßnahmen“).
* **Lange Aufenthalte auf einen Flur:** Bei der Flurwahl zählt, wer dort im Zeitraum wohnt – Hauptmaßnahmen und
  lange Aufenthalte kommen bevorzugt auf Flure, auf denen schon lange Aufenthalte wohnen, kurze auf die anderen.
  So pendelt es sich mit jeder Planung weiter ein. Das ist ein Wunsch, keine feste Regel: Geht es nicht anders
  (oder würde sonst jemand kein Zimmer bekommen), kommt die Person auf einen gemischten Flur.

* **Von Hand geht jedes freie Zimmer:** In der Zimmerauswahl stehen oben alle zulässigen Zimmer (nach Haus und
  Nummer), darunter – abgesetzt – alle übrigen Zimmer mit freiem Bett als **Ausnahme** mit kurzem Grund
  („Gästezimmer“, „nur EMR“, „andere Gruppe“, „nur Männer“ …). Wird eines gewählt, steht bei der Person ein Hinweis.
  Zimmer, in denen im Zeitraum schon jemand anderes wohnt, werden nicht angeboten.
* **Mausrad:** Über Auswahllisten und Zahlenfeldern verstellt das Mausrad nichts – die Tabelle bzw. Seite scrollt
  weiter. Erst in der per Klick geöffneten Liste wirkt das Rad.
* Tiere nur in Haus 3.1 EG/UG – das geht der Gruppenregel vor (auch EMR mit Tier wohnt dort,
  zuerst im UG) · Zimmer mit Bad über den Flur (Haus 6: x01, x02, x05, x08,
  x09) nur Männer · Doppelzimmer teilen sich nur Personen derselben UWT-Klasse und desselben
  Geschlechts – bei Klassen mit DZ-Liste nur die eingetragenen Partner –, UWT ohne Partner wohnen allein darin · nach jeder Abreise ein Tag Puffer
  (einstellbar).
* Wünsche: eine Anreise zusammen auf einem Flur (Flure = durch das Treppenhaus getrennte
  Hälften), Zimmer möglichst nicht direkt nebeneinander · kurze Maßnahmen und Assessment
  bevorzugt Haus 2 Etage 5 · Doppelzimmer für die UWT, Tier-Zimmer und Haus 2 Etage 1–2 (EMR)
  möglichst freihalten.
* **Zurücknehmen** (Zuteilen → „Zurücknehmen“): Planung der gewählten Anreise entfernen, alle kommenden
  UWT-Planungen entfernen oder alle kommenden UWT neu automatisch zuteilen. Zurückgenommene UWT werden
  nicht wieder von selbst zugeteilt. Einzelne Personen: im Feld „Zimmer“ „— nicht zugeteilt —“ wählen und
  übernehmen.
* **Konflikte mit dem Gebäudeplan:** Beim Planen gibt es keine Überschneidung (Gebäudeplan, Sperrungen,
  Zimmer-Pivot, eigene Planungen, Puffer). Bucht der Gebäudeplan später jemand anderen in ein geplantes
  Zimmer oder sperrt es, erscheint oben im Zimmerplan ein roter Hinweis (und die Zahl in der Seitenleiste);
  „Neu planen“ sucht für die Betroffenen – DZ-Partner mit – ein freies Zimmer und speichert es.
* Findet sich kein zulässiges Zimmer, bleibt die Person unzugeteilt und der Grund wird
  angezeigt – dann im Feld „Zimmer“ von Hand festlegen.
* Geschlecht steht in den Listen nicht; es wird aus dem Vornamen geschätzt (mit * markiert)
  und lässt sich korrigieren. Tiere werden aus den Bemerkungen erkannt („Hund“, „Katze“ …);
  Bemerkungen, die später kommen, unter Daten & Import an der Person ergänzen.
* Ohne Abreise wird eine übliche Dauer angenommen (**EMR: Anreise am Vortag des
  Listendatums, 3 Übernachtungen**, Assessment 4 Wochen,
  RVL/RVT 13 Wochen, sonst 1 Jahr) und mit ≈ gekennzeichnet.

**Zimmer-Pivot (optional):** Pivot mit der Belegung je Zimmer und Tag („Zimmer-Pivot
importieren“). Sie enthält keine Namen und keine UWT/Mieter, dafür jede gebuchte Nacht. Tage, die
dort belegt sind, im Gebäudeplan aber nicht, gelten als „belegt laut Zimmer-Pivot“ und werden
nicht vorgeschlagen; eine Zimmerfreigabe im Gebäudeplan hat Vorrang.

**Häuser:** alle Zimmer je Haus, Etage und Flur mit Status an einem frei wählbaren Tag
(frei, teilweise, belegt, geplant, gesperrt), Tooltip mit Bewohnern und „frei bis“.

**Zimmer-Stammdaten:** Flur, Betten, Bad über den Flur, Tier-Zimmer, Gästezimmer und „im
Internat“ (z. B. Etagen der Jugendhilfe ausblenden) – aus den Grundrissen vorbelegt, bitte
einmal prüfen. Gespeichert werden nur Abweichungen (`zimmer_stammdaten.json`).

### Inventar (neu)

Eigene Seite **Inventar** (Seitenleiste unter Verwaltung) mit drei Reitern:

* **Zimmer** – Zimmer nach Haus filtern oder suchen (auch nach Gegenstand, „nur ohne Ausstattung“), ein oder
  mehrere Zimmer wählen (Strg/Umschalt + Klick, „Alle angezeigten wählen“) und darunter die Ausstattung
  bearbeiten: Gegenstand + Anzahl hinzufügen (optional **je Bett** – Doppelzimmer bekommen doppelt so viel),
  Anzahl ändern, entfernen. **Ausstattung übernehmen von Zimmer …** kopiert die komplette Ausstattung eines
  Musterzimmers in alle gewählten Zimmer.
* **Gegenstände** – was zum Inventar gehört (Name, Kategorie, optional Bestand, Notiz). Mit Bestand zeigt das
  Programm, wie viele noch im Lager sind, und warnt, wenn mehr verteilt als vorhanden ist. „Wo steht das?“
  listet die Zimmer je Haus.
* **Übersicht** – Stück je Haus, gesamt, Bestand, Lager; **Excel** (Zimmer × Gegenstand, Gegenstände, Liste je
  Zimmer) und **Inventarliste** je Zimmer zum Abhaken beim Rundgang (alle Häuser oder ein Haus; Druck/PDF).

Die Ausstattung steht auch im Zimmer-Fenster des Zimmerplans. Gespeichert in `inventar.json`.

Zimmer werden überall nach Haus und Nummer sortiert angezeigt; West/Ost wird nicht mehr angezeigt (der Flur
bleibt intern, damit eine Anreise zusammen untergebracht wird, und ist unter Zimmerplan → Zimmer pflegbar).

### Suche nach Name oder Zimmer

Oben in der Seitenleiste „Name oder Zimmer …“ (Strg+F):
* **Name** („Meier“, „Anna Kolmer“): findet Personen in Anreiselisten, UWT-Listen, Gebäudeplan und
  Zimmerplan – mit Zimmer, Zeitraum, Status (im Haus / kommt / abgereist), Quelle und Notiz.
* **Zimmer** („322“, „2-322“, „3.1-E01“, „E01“): alle Zimmer mit der Nummer in allen Häusern – wer drin
  ist und wer kommt, leere Zimmer als „frei“ (bis zur nächsten Anreise), Doppelzimmer mit freien Betten,
  gesperrte Zimmer.
„Öffnen“ (oder Doppelklick) zeigt die Zimmer- und Personenkarte, „Im Zeitstrahl“ das Zimmer im Zeitstrahl.

**Personendialog** (Daten → Anreisen, „Alle Angaben …“ in der Karte):
* **Zimmer direkt ändern:** oben die Zimmerauswahl wie beim Zuteilen – zulässige Zimmer, unter dem Strich
  Ausnahmen mit kurzem Grund, „– kein Zimmer –“ nimmt die Planung zurück. „Speichern“ übernimmt sofort
  (Änderungsprotokoll, Aufgaben → Eintragen). Steht die Person schon im Gebäudeplan, zeigt der Dialog das
  gebuchte Zimmer – ein Umzug gehört dann ins Belegungssystem.
* **Notizen mit Wiedervorlage:** beliebig viele Notizen je Person (mit Datum); mit „Wiedervorlage am“
  erscheint die Notiz an diesem Tag als Erinnerung im Terminkalender (Seite Termine, Windows-Benachrichtigung,
  „Erledigt“ zum Abhaken; „Öffnen“ führt zurück zur Person). Die Suche zeigt Notizen und nächste
  Wiedervorlage in der Spalte „Notiz“.

### Termine und Erinnerungen (neu)

Eigene Seite **Termine** – ein Terminkalender im Dashboard, der **ohne Outlook** funktioniert.

* **Notizen zur Anreise** aus den Anreiselisten („Duschstuhl“, „kommt mit Partner“, „Anr. 20.10.“ …)
  werden automatisch zu Erinnerungen: Standard 3 Tage vor der Ankunft (einstellbar; EMR am
  Vortag des Listendatums). Notizen lassen sich an der Person ergänzen oder ändern
  (Daten & Import → Anreisen, oder „Bearbeiten“ auf der Seite Termine) – eine geänderte Notiz
  erinnert erneut.
* **Abreisen automatisch:** Für jede Abreise (Personen mit Internat und UWT-Blöcke) gibt es eine
  gesammelte Erinnerung je Tag, z. B. „Abreise: 7 Personen (EMR ASS)“ – EMR 1 Tag vorher, alle
  anderen 2 Tage vorher (Termine → Einstellungen, auch „keine Erinnerung“ möglich).
* **Persönliche Abreise-Erinnerungen** wie bisher je Person; Vorgabe ist jetzt „Terminkalender im
  Dashboard“ (eine frühere Outlook-Vorgabe wird einmalig umgestellt).
* **Eigene Termine** mit „+ Termin“: Datum, Notiz und „Erinnern X Tage vorher“.
* Anreisetage und UWT-Blöcke stehen ohne Erinnerung mit im Kalender.
* **Kalender** (Monat/Woche): Klick auf einen Tag öffnet die Tagesansicht mit allen Einträgen, Erledigt /
  Wieder offen / Öffnen. Volle Tage fassen gleiche Einträge zusammen („Notiz zur Anreise: 5“).
  **Liste** mit Filter („Erledigte zeigen“ für Zurückgenommenes).
* Nach „Erledigt“ erscheint oben **Rückgängig** – für versehentliche Klicks.
* Fällige Erinnerungen stehen oben unter „Jetzt erinnern“ und kommen jeden Tag wieder, bis sie
  abgehakt sind. Dazu eine **Windows-Benachrichtigung** beim Start und alle 15 Minuten, sobald
  etwas Neues fällig wird; die Seitenleiste zeigt die Anzahl („Termine (3)“).
* Beim Schließen läuft das Dashboard im **Infobereich** (unten rechts) weiter – Beenden per
  Rechtsklick auf das Symbol. Unter Termine → Einstellungen kann es **mit Windows starten**
  (unsichtbar im Infobereich), damit Erinnerungen auch kommen, wenn man es nicht öffnet.
  Ein zweiter Start holt nur das laufende Fenster nach vorn.

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
(Holl, Dunkel, Hochkontrast, System – live umschaltbar ohne Neuaufbau), Diagramme mit
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
3. **Tab** im Eingabefeld übernimmt den ersten Vorschlag, erneutes Tab den nächsten
   (Umschalt+Tab zurück). Mit angefangenem Text wird ergänzt: „Belegung Gos“ → „Belegung Goslar“.
4. Themenfremdes („Erzähl einen Witz“, Rollenwechsel-Versuche) wird abgelehnt.

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
  zimmerpivot.py     Zimmer-Pivot (Belegung je Zimmer und Tag)
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
