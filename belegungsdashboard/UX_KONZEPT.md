# UX- und Workflow-Konzept (Stand 6.13.0, 15.10.2026)

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
| 13 | „Quellen“ (Zimmerplan) und „Daten & Import“ (Seitenleiste) klingen gleich. | Orientierung | offen (siehe B.3) |
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
