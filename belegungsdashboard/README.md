# Belegungsdashboard 4.0

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
  im Gebäudeplan fehlt.
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
  Geplant / Gesperrt mit Anzahl. Klick auf ein Zimmer zeigt, wer wann darin wohnt (Liste und
  Zeitstrahl über drei Monate).
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
| RVL | bevorzugt Haus 3.1, sonst 3.2, 3.3 oder Haus 2 |
| Assessment, RVT, Reha-Maßnahmen | Haus 2 (Etage 1–5), 3.1, 3.2, 3.3 – nicht Haus 6 |

* **Von Hand geht jedes freie Zimmer:** In der Zimmerauswahl stehen oben alle zulässigen Zimmer (nach Haus und
  Nummer), darunter – abgesetzt – alle übrigen Zimmer mit freiem Bett als **Ausnahme** mit kurzem Grund
  („Gästezimmer“, „nur EMR“, „andere Gruppe“, „nur Männer“ …). Wird eines gewählt, steht bei der Person ein Hinweis.
  Zimmer, in denen im Zeitraum schon jemand anderes wohnt, werden nicht angeboten.
* **Mausrad:** Über Auswahllisten und Zahlenfeldern verstellt das Mausrad nichts – die Tabelle bzw. Seite scrollt
  weiter. Erst in der per Klick geöffneten Liste wirkt das Rad.
* Tiere nur in Haus 3.1 EG/UG – das geht der Gruppenregel vor (auch EMR mit Tier wohnt dort,
  bevorzugt im EG) · Zimmer mit Bad über den Flur (Haus 6: x01, x02, x05, x08,
  x09) nur Männer · Doppelzimmer teilen sich nur Personen derselben UWT-Klasse und desselben
  Geschlechts – bei Klassen mit DZ-Liste nur die eingetragenen Partner –, alle anderen wohnen allein darin · nach jeder Abreise ein Tag Puffer
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
„Zimmer anzeigen“ springt zum Zimmer, „Person öffnen“ zu Abreise, Erinnerung und Notiz.

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
