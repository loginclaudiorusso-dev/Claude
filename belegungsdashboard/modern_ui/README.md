# Neue Oberfläche (modern_ui) – Version 0.2.0

Eine neue, ruhige Oberfläche für die tägliche Zimmerverteilung. Sie liegt in einem eigenen Ordner und
**ändert keine Datei des bisherigen Programms**. Daten und Regeln kommen aus dem Hauptprogramm im Ordner
darüber (`belegung`): dieselben Dateien, dieselben Zuteil-Regeln, dasselbe Rückgängig.

## Starten

`modern_ui\Start.bat` doppelklicken. Beim ersten Start wird eine eigene Python-Umgebung (`modern_ui\.venv`)
angelegt, ca. 1–3 Minuten. Das bisherige Programm startet weiter über `Start.bat` im Hauptordner.

* Eigenes Fenster über pywebview (Edge WebView2, bei Windows 10/11 dabei).
* Lässt sich pywebview nicht installieren, öffnet sich ein Edge-Fenster ohne Adressleiste. Läuft komplett
  offline auf dem eigenen Rechner (127.0.0.1), nichts geht ins Internet.
* Bitte **nicht gleichzeitig** mit dem bisherigen Programm Zuteilungen ändern. Die neue Oberfläche lädt von
  selbst neu, wenn das Hauptprogramm etwas gespeichert hat (alle 30 Sekunden geprüft).

## Was es kann

| Bereich | Verhalten |
|---|---|
| Anreisen | Auswahl der Anreise oben (‹ › blättert), Tabelle mit Name, Gruppe, Zeitraum, Zimmer, Hinweis |
| Kennzahlen | eine Zeile: frei · belegt · gesperrt am Anreisetag |
| Filter | Alle · Handlungsbedarf · Mängel · Ohne Zimmer (mit Anzahl) |
| Zimmer in der Zeile | Auswahl speichert sofort; nur Zimmer, die die Regeln erlauben (Ausnahmen grau dahinter) |
| Grüner Vorschlag | „2-317 nehmen“ bei Personen ohne Zimmer und bei Konflikten; oben „Alle Vorschläge übernehmen“ |
| Konflikt | roter Rahmen am Zimmer + Grund (z. B. inzwischen unbewohnbar) + grünes Ausweichzimmer |
| Aufgaben-Center | rechts, schiebt die Tabelle zur Seite statt sie zu verdecken; öffnet sich einmal am Tag von selbst, wenn Dringendes neu ist; Knopf „Aufgaben“ (Taste A) |
| 1-Klick-Lösungen | Vorschläge übernehmen, Ausweichzimmer zuweisen, Reinigungen als erledigt markieren, Erinnerung erledigt |
| Später | blendet eine Aufgabe bis morgen aus |
| Rückgängig | im Hinweis unten nach jeder Änderung, oben rechts oder Strg+Z |

### Seiten (neu in 0.2.0)

| Seite | Inhalt |
|---|---|
| Zeitstrahl | Zimmer eines Hauses über 2, 4 oder 8 Wochen: belegt, im Programm geplant, gesperrt, Konflikt (rot); Punkt am Zimmer bei Mängeln; ‹ Heute › blättert wochenweise |
| Reinigung | Heute / Diese Woche / Nächste Woche, nach Frist sortiert; Häkchen = gereinigt (Rückgängig möglich); „Alle eiligen als gereinigt markieren“; Zimmer von Hand hinzufügen (Panel rechts) und wieder entfernen; Drucken |
| Mieter | Verträge mit Status; „Mail vorbereiten“ öffnet den Entwurf zum Vertragsende in Outlook (Panel rechts, Text änderbar) und vermerkt ihn; weitere Mieter laut Gebäudeplan |
| Auswertung | freie Zimmer je Woche (jetzt und nach Planung, EMR, Doppel) mit Ampel; Belegung heute je Haus |
| Verwalten | Datenstand, Datenordner öffnen; neuer Gebäudeplan im Ordner: prüfen und übernehmen (Unterschiede, Wahl je eigenem Eintrag); Einstellungen Reinigungstag und Puffer |

Formulare öffnen sich im Panel rechts – nichts legt sich über die Tabelle. Verträge anlegen/verlängern,
Unterlagen, Importe von Listen und das Eintragen fürs Firmenprogramm bleiben vorerst im Hauptprogramm.

Aufgaben ohne 1-Klick-Lösung (z. B. „Buchungen im Belegungssystem eintragen“) zeigen „Im Hauptprogramm erledigen“.

## Aufbau

| Datei | Inhalt |
|---|---|
| `app.py` | Start (Fenster bzw. Edge-Fallback), Protokoll in `modern_ui.log` |
| `modern/kern.py` | Brücke zur Logik des Hauptprogramms, ohne Oberfläche – testbar |
| `modern/oberflaeche.py` | Rahmen (Seitenleiste, Kopf, Panel rechts, Hinweis mit Rückgängig) und Seite Anreisen |
| `modern/seiten.py` | Seiten Zeitstrahl, Reinigung, Mieter, Auswertung, Verwalten |
| `modern/seiten_kern.py` | Daten dieser Seiten, ohne Oberfläche – testbar |
| `modern/ui_bausteine.py` | Knopf, Segmented Control, Leer-Hinweis |
| `modern/stil.py` | Farben und Stil (dunkel), alle Farbwerte nur hier |
| `tests/` | Tests mit erfundenen Namen: `python -m pytest modern_ui/tests` |

Eigene Ablage: `modern_ui.json` im Datenordner (nur „Später“ und „heute schon gezeigt“).

## Rückgängig machen / entfernen

Die neue Oberfläche ist ein Zusatz. Den Ordner `modern_ui` löschen genügt – das bisherige Programm und
seine Daten bleiben, wie sie sind. Sicherungen: vor 0.1.0 Branch `backup/v6.28.0`
(`INNternat_v6.28.0_Sicherung.zip`), vor 0.2.0 Branch `backup/modern-0.1.0` (`INNternat_modern-0.1.0_Sicherung.zip`).

## Nächste Schritte

1. Strg+K: Suchen und Befehle (Person, Zimmer, Seite).
2. Eintragsliste fürs Firmenprogramm als 1-Klick-Lösung.
3. Im Zeitstrahl: Klick auf eine Belegung zeigt Person/Zimmer, Umzug per Ziehen.
4. Mieter: Vertrag anlegen und verlängern.
