# UX- und Workflow-Konzept (Stand 6.14.0, 15.10.2026)

Teil 1 (6.13): sichere, nachvollziehbare Änderungen. Teil 2 (6.14): ruhige, aufgabenorientierte Oberfläche.

Ziel: Die fachliche Tiefe bleibt, die Bedienung wird vorhersehbar. Vor allem dürfen Änderungen an Zimmern nichts
unbemerkt mit verändern. Leitlinie des Nutzers: **kein kompletter Programmumbau**, darum wird schrittweise
umgesetzt, Kritisches zuerst.

## Phase A – Bestandsaufnahme

### Wege, auf denen sich ein Zimmer ändert (vom Klick bis zur Datei)

| Einstieg | Ablauf bis zur Speicherung | Datei |
|---|---|---|
| Zuteilen → Übernehmen | `vorschlagen` → `zuweisungen_speichern` (ersetzt alle Personen der Anreise) + `zuweisungen_entfernen` (wer im Vorschlag kein Zimmer hat) | `zimmer_zuweisungen.json` |
| Zeitstrahl ziehen (geplant, noch nicht da) | `verschieben_pruefen` → Rückfrage (DZ-Partner mit?) → `zuweisungen_speichern` | dto. |
| Zeitstrahl ziehen / Rechtsklick (eingezogen) | Umzug-Dialog → `umzug.pruefen` → `umzug.speichern` | `importe/umzuege.json` |
| Personen-/Zimmerkarte → Zimmer wählen | `zuweisung_setzen` | `zimmer_zuweisungen.json` |
| Person bearbeiten (Dialog) | `zuweisung_setzen` + Personendaten | dto. + Anreiseliste |
| Aufgaben → Konflikte lösen | `neu_planen` (plant Betroffene **und DZ-Partner** neu, speichert sofort) | `zimmer_zuweisungen.json` |
| Optimieren → Übernehmen | `optimierung.umsetzen` (Planungen, Tausch-Umzüge, Aufgaben) | Zuweisungen, Umzüge, Termine |
| Posteingang → Mail umsetzen | `zuweisung_setzen` / `zuweisungen_entfernen` | `zimmer_zuweisungen.json` |
| „fest“ ↔ „geplant“ | `status_setzen` (Person bzw. Umzug, Tausch beide) | Zuweisungen bzw. Umzüge |

### Gefundene Probleme – nach Risiko geordnet

| # | Problem | Risiko | Status |
|---|---|---|---|
| 1 | **„Neu“ + „Übernehmen“ überschrieb gespeicherte Zimmer ohne Rückfrage**. Auch „fest“ markierte Planungen waren betroffen, und „fest“ ging dabei still verloren. Mit echten Daten (Anreise 26.10.): 19 Personen wären umgeplant worden. | hoch | behoben: Vorschau |
| 2 | Übernehmen entfernte gespeicherte Zimmer, sobald der Vorschlag für die Person keins fand. | hoch | behoben: Vorschau „Planung wird entfernt“ |
| 3 | **„Konflikte lösen“ plante sofort neu**, auch die DZ-Partner ohne Konflikt. Wer kein Zimmer fand, verlor die Planung. Gezeigt wurde nur eine Meldung danach. | hoch | behoben: Vorschau vor dem Speichern |
| 4 | **Veralteter Stand**: Zuteilen speicherte den Vorschlag vom Öffnen der Seite. Was inzwischen in einem anderen Fenster geändert wurde, wurde überschrieben. | mittel | behoben: Vergleich mit frischem Stand, Konflikt |
| 5 | Von Hand gesetzte Zimmer (Karte, Posteingang) wurden nicht auf Doppelbelegung geprüft. | mittel | behoben: `zuweisung_setzen` lehnt ab |
| 6 | Das Protokoll wurde vor dem Speichern geschrieben. Schlug das Speichern fehl, stand dort eine Änderung, die es nicht gab. | mittel | behoben: Protokoll erst danach |
| 7 | Brach ein Speichern aus mehreren Schritten mittendrin ab (z. B. Netzlaufwerk weg), blieb ein halber Stand zurück. | mittel | behoben: Stand davor wird wiederhergestellt |
| 8 | Es gab kein Rückgängig. Fehler ließen sich nur von Hand zurückbauen. | mittel | behoben: Rückgängig (Meldung, Strg+Z) |
| 9 | „Planung entfernen“ in der Personenkarte ging ohne Rückfrage. „fest“ verschwand beim Zimmerwechsel ohne Hinweis. | niedrig | behoben |
| 10 | „Umzug zurücknehmen“ nahm bei einem Tausch den Gegen-Umzug ohne Hinweis mit zurück. | niedrig | behoben: wird genannt |
| 11 | Umzug-Dialog: Ein Doppelklick auf „Speichern“ konnte doppelt auslösen. | niedrig | behoben |
| 12 | Der Zimmerplan hat 8 gleichrangige Reiter ohne Ordnung, und welcher wofür da ist, steht nirgends. | Orientierung | verbessert: 3 Gruppen + Tooltips |
| 13 | „Quellen“ (Zimmerplan) und „Daten & Import“ (Seitenleiste) klingen gleich. | Orientierung | behoben in 6.14 (Teil 2) |
| 14 | Dieselbe Aktion hat an verschiedenen Orten verschiedene Begriffe (verschieben / umziehen / Zimmer ändern). | Orientierung | teilweise (Meldungen jetzt einheitlich „alt → neu“) |

Rechte und Berechtigungen gibt es im Programm nicht (eine Person, lokale Dateien). Die Überarbeitung führt auch
keine ein.

## Phase B – Konzept

### B.1 Ein Ablauf für jede Änderung an Zimmern

```
Auswahl  →  Prüfen (Regeln, frei?)  →  [Vorschau, wenn mehr als das Angeforderte passiert]  →  Speichern (alles
oder nichts)  →  Meldung „alt → neu“ + Rückgängig
```

* **Einfach bleibt einfach:** Wer nur Personen ohne Zimmer neu plant, sieht keinen Dialog, nur die Meldung mit
  „Rückgängig“.
* **Vorschau** (`aenderungen.zuweisungen_vorschau`, `ui/aenderung_ui.VorschauDialog`) trennt:
  1. *Angefordert*: von Hand gewählt. „Vorschlag“ heißt: kommt aus dem automatischen Vorschlag.
  2. *Zwingende Folgen* (grau): „fest“ entfällt, das alte Zimmer wird frei. Rückt jemand aus derselben
     Zuteilung nach, wird nichts frei.
  3. *Konflikte* (rot, blockieren): Zielzimmer inzwischen belegt oder gesperrt, inzwischen woanders geändert,
     zwei Personen ins selbe Einzelzimmer.
  4. *Optionale Folgen* werden nie automatisch ausgeführt. Den DZ-Partner mitzunehmen ist eine eigene Wahl
     („Beide verschieben“ / „Nur …“).
* **Speichern** (`aenderung_ui.ausfuehren`): Vorher wird der Stand gemerkt. Bei einem Fehler wird er wieder
  hergestellt, und es gibt keine Erfolgsmeldung. Eine fachliche Ablehnung (ValueError) erscheint als Hinweis.
* **Rückgängig** (`aenderungen.rueckgaengig`): Es spielt den gemerkten Stand der Planungsdateien (Zuweisungen,
  Umzüge, UWT-Automatik) Byte für Byte zurück. Das geht **nur**, wenn danach nichts anderes gespeichert wurde.
  Sonst wird es abgelehnt, mit Verweis aufs Änderungsprotokoll. So überschreibt Rückgängig nie fremde Änderungen.
  Es kann bis zu 20 Schritte, die nur in der laufenden Sitzung gelten. Die Optimierung lässt sich nur rückgängig
  machen, wenn sie keine Aufgaben angelegt hat, weil die außerhalb der Zimmerplanung liegen.
* **Nachvollziehbar:** Das Änderungsprotokoll (Zimmerplan → Quellen) gab es schon, mit wer/wann/alt/neu.
  Rückgängig erscheint dort ebenfalls.

### B.2 Reiter im Zimmerplan nach Aufgaben

| Gruppe | Reiter | Wofür |
|---|---|---|
| **Planen** | Zuteilen · Zeitstrahl · Häuser | Zimmer vergeben, umplanen, Belegung ansehen |
| **Erledigen** | Aufgaben · Abreisen · Reinigung | Tagesgeschäft: eintragen, Konflikte, Listen |
| **Verwalten** | Zimmer · Quellen | Stammdaten, Zimmerliste, Importe, Protokoll |

Ein senkrechter Strich trennt die Gruppen. Jeder Reiter sagt im Tooltip, wofür er da ist. Die Reiter werden
über ihren Namen gemerkt, eine geänderte Reihenfolge verliert also keine offenen Tabs. Alte Nummern von vor 6.10
werden umgerechnet.

### B.3 Nächste Schritte (vorgeschlagen, nicht umgesetzt)

1. „Quellen“ in „Importe & Protokoll“ umbenennen oder mit „Daten & Import“ zusammenlegen. Erst nach Rückmeldung,
   denn der Nutzer kennt die Stelle.
2. Eine Personenkarte als einziger Einstieg für „Zimmer ändern / Umzug / fest“. Zeitstrahl-Menü und Aufgaben
   öffnen dann nur noch die Karte.
3. Begriffe vereinheitlichen: „Zimmer ändern“ (noch nicht eingezogen) und „Umzug“ (eingezogen) überall gleich.
4. Rückgängig sitzungsübergreifend? Nur mit eigener Historie (Datenschutz: Namen im Datenordner bleiben lokal).

## Prüfung

* `tests/test_aenderungen.py` (14 Tests, erfundene Namen):
  * freies Zimmer
  * Wechsel ändert nur die Person
  * belegtes Ziel wird abgelehnt
  * Überschneidung
  * Folgen werden angezeigt
  * gleichzeitige Änderung
  * Rückgängig exakt bzw. abgelehnt
  * Tausch
  * Fehler mittendrin
  * Protokoll nur nach Erfolg
  * Konflikt-Vorschau speichert nichts
  * Reiter
* Oberfläche mit einer Kopie der echten Daten:
  * Abbrechen ändert nichts.
  * Bestätigen speichert.
  * Ein zweites Übernehmen ändert nichts.
  * Rückgängig stellt den Stand davor her.
  * Ein belegtes Zimmer wird abgelehnt.
  * Kein Überlauf bei 1000 px, 100/125/150 %, in allen Designs.


---

# Teil 2 – Eine ruhige, aufgabenorientierte Oberfläche (6.14)

## Analyse: Was konkurriert um Aufmerksamkeit?

Gemessen an der Oberfläche von 6.13 mit echten Daten (Kopie):

| Bereich | Vorher | Problem |
|---|---|---|
| Start | 7 Kacheln gleicher Größe und Lautstärke, je mit Liste und Link | Was zuerst zu tun ist, steht nirgends. Alte Erinnerungen (09.10.) wirken so wichtig wie 21 Personen ohne Zimmer. |
| Seitenleiste | 11 Einträge in „Analyse“ / „Verwaltung“ | Das tägliche Werkzeug (Zimmerplan) stand zwischen Termine und Inventar. |
| Zimmerplan | 8 Reiter, Kopf mit 2 Knöpfen, 5 Kennzahlen, Hinweise | „Quellen“ ist eigentlich Import, Einstellung und Protokoll in einem und doppelt sich mit „Daten & Import“. |
| Zuteilen | 5 Knöpfe gleichzeitig (Person, Neu, Zurücknehmen ▾, Export ▾, Übernehmen) | Nur „Übernehmen“ ist die Hauptaktion. Person hinzufügen, neu vorschlagen und zurücknehmen braucht man selten. |
| Daten & Import | 5 Reiter, Statistik und Zimmerplanung gemischt | Ohne Pivot-Datei blieben auch die Anreisen leer. |
| Zimmerwechsel | Zeitstrahl: Prüfung + DZ-Partner-Frage. Personenkarte: ohne beides. Drei Begriffe. | Zwei Abläufe für dieselbe Aufgabe. |

### „Quellen“ und „Daten & Import“ nach Funktion

| Funktion | vorher | Art | jetzt |
|---|---|---|---|
| Gebäudeplan, ZKL, Zimmer-Pivot importieren | Zimmerplan → Quellen | Import | Daten & Import → Gebäudeplan & ZKL |
| Anreiselisten, UWT | Daten & Import | Import | unverändert, links (Zimmerplanung) |
| Pivot, Kapazitäten, Mieten, manuelle Einträge | Daten & Import | Import/Eingabe Statistik | rechts, abgetrennt (Statistik) |
| Puffer, Facility-Check | Zimmerplan → Quellen | Einstellung | Einstellungen → Zimmerplanung |
| Änderungsprotokoll | Zimmerplan → Quellen | Nachvollziehen | Zimmerplan → Mehr → Verlauf (mit Rückgängig) |

Ergebnis: Beide Bereiche dienten derselben Aufgabe, nämlich Daten ins Programm zu holen. Sie sind jetzt
**zusammengeführt**. Was keine Importe waren, steht dort, wo man es sucht.

## Konzept

1. **Start „Heute“ – Vorgangsliste nach dem Feed-Prinzip.** Übernommen werden nur die nützlichen Prinzipien:
   * Ein Eintrag ist ein Vorgang mit Titel, einer Zeile Detail und genau einer Aktion.
   * Gleiches wird gebündelt („27 Buchungen eintragen“).
   * Drei Stufen, nach Dringlichkeit und dann Art geordnet (Konflikte → Zimmer vergeben → eintragen/Posteingang →
     Engpässe → Erinnerungen):
     * „Zuerst klären“: rote Punkte, Aktion als Hauptknopf
     * „Als Nächstes“
     * „Zur Info“: eingeklappt
   * Die Aktion springt direkt an die Bearbeitungsstelle: die Anreise in „Zuteilen“, die Konflikt-Vorschau, die
     Personenkarte, den Posteingang. Erinnerungen lassen sich in der Zeile abhaken.
   * Die frei zusammenstellbaren Kacheln bleiben als „Übersicht“. Die gewählte Ansicht wird gemerkt.
   * Logik: `belegung/vorgaenge.py` (ohne Qt, getestet), aus denselben Quellen wie die Kacheln.
2. **Navigation nach Aufgaben.**
   * Seitenleiste: Arbeiten (täglich) · Auswerten · Verwalten (selten).
   * Zimmerplan: 7 Reiter in 3 Gruppen.
   * Seltenes liegt unter „Mehr“: Verlauf, neues Fenster, Sprung zu Importen und Einstellungen.
3. **Eine Hauptaktion je Ansicht.**
   * „Zuteilen“: Übernehmen (Hauptknopf), Export; alles Weitere unter „Mehr“.
   * Daten & Import: je Reiter eine Hauptaktion (Hochladen/Importieren).
4. **Zimmerwechsel: ein Prozess, zwei sinnvolle Einstiege.** Entschieden nach dem Arbeitsablauf:
   * **Planen** (Personen ohne Zimmer): „Zuteilen“. Das ist die erste Vergabe, nicht ein Wechsel.
   * **Wechsel, noch nicht eingezogen:** Zeitstrahl (ziehen oder Rechtsklick „Zimmer wechseln …“) oder Personenkarte.
     Beides läuft durch `aenderung_ui.zimmer_wechseln_geplant`: Regeln prüfen, nach dem DZ-Partner fragen (optional,
     nie automatisch), „vorher → nachher“ samt Folgen, Abgleich mit dem aktuellen Stand, Speichern mit Rückgängig.
   * **Wechsel, eingezogen:** „Zimmer wechseln (Umzug ab …)“ öffnet überall denselben Umzug-Dialog.

   Der Zeitstrahl bleibt Einstieg, weil man dort freie Zeiträume sieht. Die Personenkarte bleibt Einstieg, weil man
   dort von der Person ausgeht. Beide nutzen denselben Ablauf, es gibt also keine zwei Logiken.

## Umgesetzt in 6.14 / bewusst nicht

* Umgesetzt: alles aus dem Konzept oben.
* Nicht umgebaut:
  * Zeitstrahl, Häuser, Aufgaben, Reinigung, Abreisen: diese Ansichten haben schon je eine Hauptaufgabe.
  * Personen-/Zimmerkarte: Notizen, Inventar und Abreise gehören dort zur Person.
* Mögliche nächste Schritte, nur auf Wunsch:
  * Kennzahlen-Zeile im Zimmerplan auf zwei Werte kürzen (frei / nach Planung), Rest in den Tooltip.
  * „Heute“ auch im Zimmerplan als kleine Seitenleiste.
  * Engpass-Grenzen und Ampel in einer Einstellung zusammenfassen.

## Prüfung (6.14)

* Automatische Tests: 147, davon neu `tests/test_vorgaenge.py`. Abgedeckt sind:
  * Dringlichkeit und Reihenfolge der Vorgänge
  * kein Vorgang, wenn erledigt
  * Erinnerungen
  * „Zimmer wechseln“ ändert nur die gewählte Person und lehnt ein belegtes Ziel ab
  * alte Reiter-Nummern
* Mit Datenkopie durch die echte Oberfläche:
  * Heute → Zuteilen bzw. Eintragen
  * Navigation zu „Gebäudeplan & ZKL“
  * gemerkter Reiter „Quellen“ → Zuteilen
  * Zimmer wechseln + Rückgängig
  * Sortierung (179 Spaltenklicks, 0 Fehler)
* Kein Überlauf bei 1000 px, 100/125/150 %, in allen 4 Designs.
