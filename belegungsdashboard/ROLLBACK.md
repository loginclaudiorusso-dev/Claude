# Rückweg: von 6.20.0 zurück zu 6.19.0, 6.18.0, 6.17.1, 6.17.0, 6.16.0, 6.15.0, 6.14.0, 6.13.0, 6.12.0, 6.11.0, 6.10.0, 6.9.1, 6.8.0, 6.7.1, 6.6.0, 6.5.0, 6.4.0, 6.3.0, 6.2.0, 6.1.0, 6.0.0 oder 5.17.0

Jede größere Lieferung hat einen eigenen, geprüften Sicherungspunkt. Zurück geht es jederzeit, ohne Code von Hand
zu rekonstruieren – und ohne Arbeitsdaten zu verlieren (die Datenformate sind seit 5.17.0 unverändert).

## 1. Wo die Stände liegen

| Stand | Git-Branch (GitHub) | Commit | Zip-Paket (mitgeliefert) |
|---|---|---|---|
| **5.17.0** (vor dem Overhaul) | `backup/v5.17.0-vor-ui-overhaul` (auch `claude/bold-keller-8jch4a`) | `4d6bd76` | `INNternat_v5.17.0_Sicherung.zip` |
| **6.0.0** | `backup/v6.0.0` | `d40959c` | `INNternat_v6.0.0_Sicherung.zip` |
| **6.1.0** | `backup/v6.1.0` | `62ce38c` | `INNternat_v6.1.0_Sicherung.zip` |
| **6.2.0** | `backup/v6.2.0` | `601ae13` | `INNternat_v6.2.0_Sicherung.zip` |
| **6.3.0** | `backup/v6.3.0` | `4768baf` | `INNternat_v6.3.0_Sicherung.zip` |
| **6.4.0** | `backup/v6.4.0` | `0ec04da` | `INNternat_v6.4.0_Sicherung.zip` |
| **6.5.0** | `backup/v6.5.0` | `a4f6499` | `INNternat_v6.5.0_Sicherung.zip` |
| **6.6.0** | `backup/v6.6.0` | `8d45202` | `INNternat_v6.6.0_Sicherung.zip` |
| **6.7.1** | `backup/v6.7.1` | `b5658fe` | `INNternat_v6.7.1_Sicherung.zip` |
| **6.8.0** | `backup/v6.8.0` | `80dfe6b` | `INNternat_v6.8.0_Sicherung.zip` |
| **6.9.1** | `backup/v6.9.1` | `2b12e6a` | `INNternat_v6.9.1_Sicherung.zip` |
| **6.10.0** | `backup/v6.10.0` | `ed861df` | `INNternat_v6.10.0_Sicherung.zip` |
| **6.11.0** | `backup/v6.11.0` | `e401d50` | `INNternat_v6.11.0_Sicherung.zip` |
| **6.12.0** | `backup/v6.12.0` | `c6b7a12` | `INNternat_v6.12.0_Sicherung.zip` |
| **6.13.0** | `backup/v6.13.0` | `7577366` | `INNternat_v6.13.0_Sicherung.zip` |
| **6.14.0** | `backup/v6.14.0` | `85d7ffb` | `INNternat_v6.14.0_Sicherung.zip` |
| **6.15.0** | `backup/v6.15.0` | `1553db3` | `INNternat_v6.15.0_Sicherung.zip` |
| **6.16.0** | `backup/v6.16.0` | `968ca87` | `INNternat_v6.16.0_Sicherung.zip` |
| **6.17.0** | `backup/v6.17.0` | `9ee6996` | `INNternat_v6.17.0_Sicherung.zip` |
| **6.17.1** | `backup/v6.17.1` | `8ff80d4` | `INNternat_v6.17.1_Sicherung.zip` |
| **6.18.0** | `backup/v6.18.0` | `28c61fd` | `INNternat_v6.18.0_Sicherung.zip` |
| **6.19.0** | `backup/v6.19.0` | `d284505` | `INNternat_v6.19.0_Sicherung.zip` |
| **6.20.0** (aktuell) | `claude/ui-overhaul-v6` | siehe Abschnitt 5 | `INNternat_Update.zip` |

**Wichtig – Historie am 15.10.2026 bereinigt (Datenschutz):** In frühen Commits vom 03.10. standen echte Namen und
TN-Nummern in Testdaten. Diese Stellen wurden in der ganzen Git-Historie durch erfundene Namen gleicher Länge ersetzt.
Dadurch haben **alle Commits ab dem 03.10. neue Nummern**. Diese Datei nennt bereits die neuen. Der Inhalt jedes
Sicherungsstands ist Byte für Byte gleich geblieben, geprüft für alle 19 Branches. Die alte Historie liegt vollständig als
`Git-Historie_vor_Bereinigung_2026-10-15.bundle` vor (an den Nutzer übergeben; enthält echte Namen – nicht hochladen),
dazu die Zuordnung alt → neu (`commit-map_2026-10-15.txt`). Wiederherstellen ginge mit
`git clone Git-Historie_vor_Bereinigung_2026-10-15.bundle`.

Zusätzlich lokale Git-Tags `v5.17.0-sicherung`, `v6.0.0-sicherung`, `v6.1.0-sicherung`, `v6.2.0-sicherung` und `v6.3.0` (Tags lassen sich aus der
Arbeitsumgebung nicht nach GitHub pushen – die Branches oben genügen).

## 2. Schnellster Rückweg (lokal, ohne Git) – 3 Schritte

1. Dashboard beenden (auch im Infobereich unten rechts: Rechtsklick auf das Symbol → **Beenden**).
2. Das Zip des gewünschten Standes (z. B. `INNternat_v6.11.0_Sicherung.zip`) in den
   Programmordner `C:\Users\claudio.russo\Documents\GitClaude\INNternat` entpacken und alles überschreiben.
3. `Start.bat` starten – in der Seitenleiste steht die alte Versionsnummer.

Die Arbeitsdaten bleiben erhalten: Die Zips enthalten keine Zuweisungen, Termine, Notizen oder Einstellungen.
Was neuere Versionen zusätzlich in `einstellungen.json` speichern (6.1: offene Tabs `ansichten`, Kacheln
`dashboard`; 6.2: `design`, `anzeige_name`), ignorieren ältere Versionen einfach. Übrig bleiben nur harmlose neue Programmdateien (z. B.
`belegung/cockpit.py`), die ältere Versionen nicht benutzen, und der Ordner `Sicherungen/`.

**Ganz sauber (optional):** Ordner `INNternat` umbenennen (z. B. `INNternat_v61`), neuen Ordner `INNternat`
anlegen, das alte Zip hinein entpacken und die Arbeitsdaten zurückkopieren: alle `*.json` im Hauptordner, die
Ordner `importe`, `Gebaeudeplan`, `UWT`, `Listen` und – falls gewünscht – `Sicherungen`.

## 3. Arbeitsdaten zurückholen (unabhängig von der Version)

* **Ab 6.0:** Einstellungen → Datensicherung → Sicherung wählen → **Wiederherstellen …**
  Der aktuelle Stand wird vorher automatisch gesichert („vor Wiederherstellung“).
* **Von Hand (jede Version):** Dashboard beenden, aus `Sicherungen/<Datum>_<Uhrzeit>_v…/` die Dateien in den
  Programmordner kopieren (Unterordner `importe` mit).
* Jede neue Version legt beim ersten Start automatisch eine Sicherung **„vor Update“** an.

**Empfehlung vor jedem Update:** den ganzen Ordner `INNternat` kopieren (z. B. `INNternat_Sicherung_2026-10-12`).

## 4. Rückweg mit Git

```bash
git fetch origin
# einen alten Stand ansehen bzw. damit weiterarbeiten (verändert nichts am aktuellen Branch)
git switch -c arbeit-v620 origin/backup/v6.2.0
git switch -c arbeit-v610 origin/backup/v6.1.0
git switch -c arbeit-v600 origin/backup/v6.0.0
git switch -c arbeit-v517 origin/backup/v5.17.0-vor-ui-overhaul

# Änderungen seit 6.1.0 bzw. 6.0.0 zurücknehmen, ohne Verlauf umzuschreiben (Revert-Commits)
git switch claude/ui-overhaul-v6
git revert --no-edit 601ae13..HEAD
git revert --no-edit 62ce38c..HEAD
git revert --no-edit d40959c..HEAD
# … oder alles seit 5.17.0
git revert --no-edit 4d6bd76..HEAD

# nur einzelne Schritte zurücknehmen (neuester zuerst, Abhängigkeiten siehe unten)
git revert --no-edit <commit>
```

Kein `git reset --hard`, kein Force-Push nötig – die Sicherungs-Branches bleiben unverändert.

## 5. Die Schritte (je ein Commit auf `claude/ui-overhaul-v6`)

**6.0.0** (seit `4d6bd76`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `f1af493` | Daten/Infrastruktur | Datensicherung beim Start (`belegung/datensicherung.py`), `.gitignore` | – |
| `4a90ad0` | fachlich | Bewohner-Schlüssel für Gebäudeplan/UWT, Notizen auch für Zimmer | – |
| `0f29d62` | UI | Zimmer- und Personenkarte (`ui/zimmerkarte.py`, `ui/notizen.py`) | `4a90ad0` |
| `75a2e74` | UI | Mehrere Fenster, einklappbare Hinweise, Zuteilen-Leiste | `0f29d62` |
| `3df9b30` | UI | Datensicherung in den Einstellungen | `f1af493` |
| `0d04e75`, `bd2498e`, `d40959c` | Doku/Daten | Version 6.0.0, „vor Update“-Sicherung, ROLLBACK.md | – |

**6.1.0** (seit `d40959c`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `30e77b5` | UI | Eigener Kalender für Datumsfelder (`widgets.KalenderPopup`) | – |
| `fdc614a` | Leistung | Minimiert/Infobereich: nichts neu rechnen, Speicher freigeben | – |
| `0a3a3df` | UI | Tabs im Hauptfenster; kein Überlauf bei 1000 px | `fdc614a` |
| `3b86504` | UI + rein | Startseite „Mein Dashboard“ (`belegung/cockpit.py`, `ui/seiten/start.py`) | `0a3a3df` |
| `62ce38c` | Doku | Version 6.1.0, README, ROLLBACK.md | – |

**6.2.0** (seit `62ce38c`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `3e951db` | UI | Name des Dashboards änderbar; Design-Auswahl; Tab-Symbole; Reinigung-Leiste | – |
| `d1fc866`, `601ae13` | Doku | Version 6.2.0, README, ROLLBACK.md, Offene Punkte | – |

**6.3.0** (seit `601ae13`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `5ea4ed7` | UI + rein | Startseiten-Titel, KW mit Daten, Engpässe erklärt, Grenzen einstellbar | – |
| `5c99189` | rein + UI | Posteingang (`belegung/mails.py`, `ui/seiten/posteingang.py`) | – |
| `62a19b6` | fachlich | Optimierung (`belegung/optimierung.py`, `zimmer_wert_details`) | – |
| `8c696d2` | UI | Dialog „Belegung optimieren“, Knopf im Zimmerplan, Kachel | `62a19b6` |
| `4768baf` | Doku | Version 6.3.0, README, ROLLBACK.md | – |

**6.4.0** (seit `4768baf`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `2c48e73` | fachlich | Umzug während des Aufenthalts (`belegung/umzug.py`, Feld `Belegung.umzug`) | – |
| `520f2fb` | UI | Ziehen belegter Balken, Rechtsklick-Menü, Umzug-Dialog, Personenkarte | `2c48e73` |
| `6c6dcbf` | Daten | Gespeicherter Gebäudeplan bleibt für ältere Versionen lesbar (Rückweg) | `2c48e73` |
| `0ec04da` | Doku | Version 6.4.0, README, ROLLBACK.md | – |

**6.5.0** (seit `0ec04da`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `c2b8f39` | Regel | Haus 3.1 UG ausschließlich mit Tier (ohne Tier nur von Hand) | – |
| `fc29fd2` | fachlich | Optimierung: dieselbe Anreise zusammen auf einen Flur, Tausch über Gruppen | – |
| `a4f6499` | Doku | Version 6.5.0, README, ROLLBACK.md | – |

**6.6.0** (seit `a4f6499`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `594d0d2` | rein + UI | ZKL-Import und Abgleich (`belegung/zkl.py`, `ui/zkl_dialog.py`, Karte unter Quellen) | – |
| `8d45202` | Doku | Version 6.6.0, README, ROLLBACK.md | – |

**6.7.0** (seit `8d45202`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `e43d9ac` | fachlich + UI | Geplant ↔ belegt für Zuweisungen und Umzüge; ZKL-Vorauswahl | – |
| `ba85e32` | Doku | Version 6.7.0, README, ROLLBACK.md | – |
| `b5658fe` | UI | Begriff „Planung abschließen (fest)“, Fehlermeldung beim Neuladen der Zimmerkarte | – |

**6.8.0** (seit `b5658fe`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `80dfe6b` | UI | Tabellen sortierbar (`widgets.Tabelle`), Zeilen-Zuordnung an den Aufrufstellen, Doku | – |

**6.9.0** (seit `80dfe6b`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `f070321` | fachlich + UI | Je Kurs ein Flur; „Kurs zusammenführen“ (Bewohner-Tausch als Umzugspaar); Doku | – |
| `2b12e6a` | UI | Sortieren nach Auswahllisten/Häkchen in Tabellenzellen (`widgets.widget_text`) | – |

**6.10.0** (seit `2b12e6a`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `ed861df` | UI + rein | Abreiseliste (Reiter „Abreisen“, `cockpit.abreiseliste`, `drucklisten.abreiseliste_html`), Zimmer-Sortierung, kompakte Reiter | – |

**6.11.0** (seit `ed861df`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `8470f2c`, `e401d50` | rein + UI | Renovierung/Boden je Zimmer, Zimmerliste filtern & drucken (`belegung/zimmerliste.py`) | – |

**6.12.0** (seit `e401d50`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `c6b7a12` | rein + UI | „Frei nach Planung“ (`eintragen.nach_planung`), Renovierung ohne Datum, Haus 6/4. OG | – |

**6.13.0** (seit `c6b7a12`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `e6f7dbe` | rein | Protokoll erst nach dem Speichern; `zuweisung_setzen` lehnt Doppelbelegung ab; `neu_planen_vorschlag`; `belegung/aenderungen.py` (Vorschau, Rückgängig) | – |
| `18b6d89` | UI | Vorschau-Dialog, sicheres Speichern, Rückgängig (Meldung, Strg+Z); Zimmerplan-Reiter in 3 Gruppen | `e6f7dbe` |
| `4af8c66` | Doku/Tests | `tests/test_aenderungen.py`, `UX_KONZEPT.md`, Version 6.13.0 | – |
| (letzter) | Doku | Commit-Nummern in ROLLBACK.md | – |

Datenformate unverändert: 6.12 liest alles, was 6.13 schreibt. Ein Rückweg zu 6.12 ist ohne Datenverlust möglich.

**6.14.0** (seit `7577366`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `5858547` | rein | `belegung/vorgaenge.py` (Vorgänge für „Heute“) | – |
| `4df86b1` | UI | Start „Heute“; Importe nach Daten & Import (`ui/zimmerquellen.py`), Reiter „Quellen“ entfällt; Verlauf; Planungs-Einstellungen unter Einstellungen; Seitenleiste Arbeiten/Auswerten/Verwalten; Zuteilen „Mehr“; ein Ablauf „Zimmer wechseln“ | `5858547` |
| `3949e40` | Doku/Tests | `tests/test_vorgaenge.py`, `UX_KONZEPT.md` Teil 2, Version 6.14.0 | – |
| (letzter) | Doku | Commit-Nummern in ROLLBACK.md | – |

Datenformate unverändert. Neu in `einstellungen.json`: `start_ansicht` (heute/kacheln) – ältere Versionen ignorieren es.
Gemerkte Tabs mit dem Reiter „Quellen“ öffnen „Zuteilen“; nach einem Rückweg zu 6.13 ist „Quellen“ wieder da.

**6.14.1** (seit `85d7ffb`): ein Commit – Zuteilen-Knopf „Export“ heißt „Drucken“ (nur Beschriftung). Rückweg: Zip 6.14.0
oder `git revert` dieses Commits.

**6.15.0** (seit `85d7ffb`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `5f9e712` | rein | `zimmerliste.Filter`: Status am Tag, mehrere Böden, Personengruppen | – |
| `d5e9441` | UI | Reiter „Zimmer“ = `ui/zimmerfinder.py` (Übersicht/Karten/Liste, Chips), „Stammdaten“ eigener Reiter, Reiter angeheftet (`Seite.anheften`), Zuteilen „Drucken“ neben „Übernehmen“, neue Symbole | `5f9e712` |
| `b15dd67` | Doku/Tests | `tests/test_zimmerfinder.py`, Version 6.15.0 | – |
| (letzter) | Doku | Commit-Nummern in ROLLBACK.md | – |

Datenformate unverändert; neu in `einstellungen.json`: `zimmer_finder` (Ansicht, Haus). Gemerkte Tabs „Häuser“ öffnen
„Zimmer“. Die erweiterte `Renovierungen_Import.tsv` (nur im Zip) wird einmal übernommen – Rückweg für die Zimmerdaten:
Einstellungen → Datensicherung (Stand vor dem Update) oder Renovierung je Zimmer in der Liste über „Bearbeiten“ ändern.

**6.16.0** (seit `1553db3`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `2f6862f` | rein | `belegung/neuigkeiten.py`, `belegung/maengel.py`, Mängel-Filter in `zimmerliste`, Vorgang „Mängel“ | – |
| `a095a61` | UI | Glocke + Leiste (`ui/neuigkeiten_leiste.py`), Hintergrund-Meldungen dorthin, Mängel-Chips in der Zimmerkarte, Finder (Chip, Filter, FM-Liste), Symbole Farbrolle/Werkzeug | `2f6862f` |
| `aaef00e` | Doku/Tests | `tests/test_neuigkeiten_maengel.py`, Version 6.16.0 | – |
| (letzter) | Doku | Commit-Nummern in ROLLBACK.md | – |

Neu im Datenordner: `zimmer_maengel.json` und `importe/neuigkeiten.json`; in `einstellungen.json`
`neuigkeiten_offen`. Ältere Versionen ignorieren sie – nach einem Rückweg sind Mängel nicht sichtbar, bleiben aber
erhalten.

**6.17.0** (seit `968ca87`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `1a5c19c` | rein | `belegung/datenstatus.py`, `termine.dringlichkeit/gruppieren`, `zimmerplan.anzeige_name` + eindeutige Schlüssel für fehlende Namen | – |
| `a666148` | UI | Zeitstrahl-Kopf/Zoom/Filter/angeheftete Datumsleiste, Termine nach Dringlichkeit, Übersicht-KPIs/Hinweise, Datenstand in der Seitenleiste, Kontrast/Fokus, kleine Fenster | `1a5c19c` |
| `a29064b` | Doku/Tests | `tests/test_ui_617.py`, `UX_KONZEPT.md` Teil 4, Version 6.17.0 | – |
| (letzter) | Doku | Commit-Nummern in ROLLBACK.md | – |

Datenformate unverändert; neu in `einstellungen.json` nur `zs_zeitraum` (Zoom des Zeitstrahls) – ältere Versionen
ignorieren es. Gespeicherte Ansichten des Zeitstrahls öffnen in 6.16 wieder im Monat. Rückweg ohne Datenverlust.

**6.17.1** (seit `9ee6996`): ein Commit (`5277c4c`). Er enthält den einmaligen Inventur-Import (`inventar.auto_import`,
`tests/test_inventar_import.py`) und Version 6.17.1. Die Datei `Inventar_Import.tsv` liegt nur im Zip, nicht im Repo.
Der Import schreibt `inventar.json` und in `einstellungen.json` den Eintrag `inventar_importe`. Ältere Versionen lesen
beides weiter, die beiden neuen Gegenstände bleiben dann einfach im Inventar.

Rückweg für die Inventardaten: Inventar → Gegenstände → „Nachttischlampe (neu)“ bzw. „Matratze Bett1“ löschen. Das
entfernt sie aus allen Zimmern. Alternativ geht es über Einstellungen → Datensicherung (Stand vor dem Update).
Rückweg für den Code: Zip 6.17.0 oder `git revert` dieses Commits.

**6.18.0** (seit `8ff80d4`): ein Commit (`df12a2f`).
* Inhalt: `belegung/zimmerzustand.py` (einmaliger Import), Katalog „Renovierung nötig“, Reno-Monat in
  `zimmerliste`, Notizen in der Zimmerkarte, `tests/test_zimmerzustand.py`, Version 6.18.0.
* Die Datei `Zimmerzustand_Import.tsv` (aus der ZKL, mit Zimmerdaten) liegt nur im Zip.
* Der Import schreibt `zimmer_stammdaten.json`, `zimmer_maengel.json` und in `einstellungen.json` den Eintrag
  `zustand_importe`.
* Ältere Versionen:
  * Sie zeigen einen Reno-Monat („2026-08“) als „ja (Datum ?)“.
  * Den Mangel „renovierung“ zeigen sie als Rohtext.
  * Es gehen keine Daten verloren.
* Rückweg für die Daten: Einstellungen → Datensicherung (Stand vor dem Update). Einzelne Mängel lassen sich in der
  Zimmerkarte abhaken.

**6.19.0** (seit `28c61fd`): ein Commit (`d1d7d24`).
* Inhalt:
  * „!“-Filter (Finder, Zeitstrahl, Kennzahl)
  * Mängelbericht (`maengel.bericht/fm_html/fm_excel/fm_erledigte_lesen/erledigte_uebernehmen`)
  * „macht unbewohnbar“ je Mangel (`Mangel.sperrt`, `Lage.unbewohnbar`, Regel in `zimmerplan.passt`)
  * `tests/test_fm_bericht.py`, Version 6.19.0
* Daten: In `zimmer_maengel.json` kann je Mangel `sperrt` stehen.
* Ältere Versionen ignorieren `sperrt` und teilen unbewohnbare Zimmer dann wieder zu. Es gehen keine Daten
  verloren.

**6.20.0** (seit `d284505`): ein Commit (`4eddc71`).
* Inhalt:
  * `belegung/mieter.py` (Vertrag, Vordrucke mit pypdf, Nebenabrede .docx)
  * `ui/mieter_dialog.py` (Masken)
  * Mieter als Bedarf im Zimmerplan, Menüeinträge, Knopf in der Personenkarte
  * `tests/test_mieter.py`, Version 6.20.0
* Die Vorlagen in `Vorlagen/Mieter` liegen nur im Zip.
* Daten: neu ist `mieter.json` (Mietverträge); Zuweisungen mit Personenschlüssel `mv:<Nr>`.
* Ältere Versionen:
  * Sie kennen die Mieter-Bedarfe nicht und verwerfen deshalb diese Zuweisungen beim Laden. Die Mieter stehen dort
    nicht im Zimmerplan.
  * `mieter.json` bleibt erhalten. Nach erneutem Update ist alles wieder da.

## 6. Was sich geändert hat – und was nicht

* **Unverändert:** Abhängigkeiten (`requirements.txt`), Start (`Start.bat`), Datenformate, Planungsregeln,
  Import von Gebäudeplan/Anreiselisten/UWT, Statistik und Prognose.
* **Neu in den Einstellungen (6.1/6.2):** `ansichten` (offene Tabs), `dashboard` (Kacheln), `zp_hinweise_offen`,
  `design`, `anzeige_name`; 6.3: `start_titel`, `engpass_grenzen`.
* **Neu im Datenordner (6.3):** `importe/posteingang.json` (abgelegte Mails mit Prüflisten).
* **Neu in den Daten (6.11):** in `zimmer_stammdaten.json` je Zimmer `renoviert`, `boden`, `boden_vermutet`; in
  `einstellungen.json` `renovierung_importe`. Ältere Versionen ignorieren die Felder. Die Renovierungsliste
  `Renovierungen_Import.tsv` liegt nur im Zip (echte Daten – nicht im Git).
* **Neu in den Daten (6.9):** in `importe/umzuege.json` das Feld `partner` (Tauschpaar). Ältere Versionen kennen es
  nicht und zeigen die beiden Umzüge eines Tausches als „Konflikt“ – nichts geht verloren.
* **Neu in den Daten (6.7):** in `zimmer_zuweisungen.json` die Felder `status`/`belegt_am`, in `importe/umzuege.json`
  das Feld `belegt`. Ältere Versionen ignorieren sie – dort erscheint „belegt“ wieder als „geplant“.
* **Neu im Datenordner (6.6):** `importe/zkl.json` (importierte ZKL, übernommene Bewohner, geprüfte Punkte).
  Ältere Versionen ignorieren die Datei.
* **Neu im Datenordner (6.4):** `importe/umzuege.json` (geplante Umzüge). Ältere Versionen ignorieren die Datei –
  nach einem Rückweg sind geplante Umzüge dort nicht sichtbar, bleiben aber erhalten und erscheinen nach dem
  nächsten Update wieder.
* **Neu im Datenordner (6.0):** Ordner `Sicherungen/` (nur Kopien); Notizen zu Zimmern (`zimmer:<ID>`) und zu
  Gebäudeplan-Bewohnern (`gp:<Name>`) stehen wie bisherige Notizen in `termine.json`.
* **Keine** Datenbank, keine Migration, keine Zugangsdaten in Sicherungen (API-Schlüssel liegen in der
  Windows-Anmeldeinformationsverwaltung).
* Echte Daten (Gebäudeplan, Klassenübersicht, Anreiselisten, Sicherungen) sind nie im Git-Repository.
