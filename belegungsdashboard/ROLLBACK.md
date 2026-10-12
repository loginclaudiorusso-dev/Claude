# Rückweg: von 6.1 zurück zu 6.0.0 oder 5.17.0

Jede größere Lieferung hat einen eigenen, geprüften Sicherungspunkt. Zurück geht es jederzeit, ohne Code von Hand
zu rekonstruieren – und ohne Arbeitsdaten zu verlieren (die Datenformate sind seit 5.17.0 unverändert).

## 1. Wo die Stände liegen

| Stand | Git-Branch (GitHub) | Commit | Zip-Paket (mitgeliefert) |
|---|---|---|---|
| **5.17.0** (vor dem Overhaul) | `backup/v5.17.0-vor-ui-overhaul` (auch `claude/bold-keller-8jch4a`) | `2072131` | `INNternat_v5.17.0_Sicherung.zip` |
| **6.0.0** | `backup/v6.0.0` | `88e2171` | `INNternat_v6.0.0_Sicherung.zip` |
| **6.1.0** (aktuell) | `claude/ui-overhaul-v6` | siehe Abschnitt 5 | `INNternat_Update.zip` |

Zusätzlich lokale Git-Tags `v5.17.0-sicherung` und `v6.0.0-sicherung` (Tags lassen sich aus der
Arbeitsumgebung nicht nach GitHub pushen – die Branches oben genügen).

## 2. Schnellster Rückweg (lokal, ohne Git) – 3 Schritte

1. Dashboard beenden (auch im Infobereich unten rechts: Rechtsklick auf das Symbol → **Beenden**).
2. Das Zip des gewünschten Standes (`INNternat_v6.0.0_Sicherung.zip` bzw. `INNternat_v5.17.0_Sicherung.zip`) in den
   Programmordner `C:\Users\claudio.russo\Documents\GitClaude\INNternat` entpacken und alles überschreiben.
3. `Start.bat` starten – in der Seitenleiste steht die alte Versionsnummer.

Die Arbeitsdaten bleiben erhalten: Die Zips enthalten keine Zuweisungen, Termine, Notizen oder Einstellungen.
Was 6.1 zusätzlich speichert (offene Tabs `ansichten`, Kachel-Anordnung `dashboard` in `einstellungen.json`),
ignorieren ältere Versionen einfach. Übrig bleiben nur harmlose neue Programmdateien (z. B.
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
git switch -c arbeit-v600 origin/backup/v6.0.0
git switch -c arbeit-v517 origin/backup/v5.17.0-vor-ui-overhaul

# Änderungen seit 6.0.0 zurücknehmen, ohne Verlauf umzuschreiben (Revert-Commits)
git switch claude/ui-overhaul-v6
git revert --no-edit 88e2171..HEAD
# … oder alles seit 5.17.0
git revert --no-edit 2072131..HEAD

# nur einzelne Schritte zurücknehmen (neuester zuerst, Abhängigkeiten siehe unten)
git revert --no-edit <commit>
```

Kein `git reset --hard`, kein Force-Push nötig – die Sicherungs-Branches bleiben unverändert.

## 5. Die Schritte (je ein Commit auf `claude/ui-overhaul-v6`)

**6.0.0** (seit `2072131`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `178baef` | Daten/Infrastruktur | Datensicherung beim Start (`belegung/datensicherung.py`), `.gitignore` | – |
| `4098d18` | fachlich | Bewohner-Schlüssel für Gebäudeplan/UWT, Notizen auch für Zimmer | – |
| `61d77a8` | UI | Zimmer- und Personenkarte (`ui/zimmerkarte.py`, `ui/notizen.py`) | `4098d18` |
| `c5ec862` | UI | Mehrere Fenster, einklappbare Hinweise, Zuteilen-Leiste | `61d77a8` |
| `c19bbb3` | UI | Datensicherung in den Einstellungen | `178baef` |
| `db37470`, `49819ad`, `88e2171` | Doku/Daten | Version 6.0.0, „vor Update“-Sicherung, ROLLBACK.md | – |

**6.1.0** (seit `88e2171`):

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `71cbb38` | UI | Eigener Kalender für Datumsfelder (`widgets.KalenderPopup`) | – |
| `8658836` | Leistung | Minimiert/Infobereich: nichts neu rechnen, Speicher freigeben | – |
| `ccba34e` | UI | Tabs im Hauptfenster; kein Überlauf bei 1000 px | `8658836` |
| `b8132e0` | UI + rein | Startseite „Mein Dashboard“ (`belegung/cockpit.py`, `ui/seiten/start.py`) | `ccba34e` |
| (letzter) | Doku | Version 6.1.0, README, ROLLBACK.md | – |

## 6. Was sich geändert hat – und was nicht

* **Unverändert:** Abhängigkeiten (`requirements.txt`), Start (`Start.bat`), Datenformate, Planungsregeln,
  Import von Gebäudeplan/Anreiselisten/UWT, Statistik und Prognose.
* **Neu in den Einstellungen (6.1):** `ansichten` (offene Tabs), `dashboard` (Kacheln), `zp_hinweise_offen`.
* **Neu im Datenordner (6.0):** Ordner `Sicherungen/` (nur Kopien); Notizen zu Zimmern (`zimmer:<ID>`) und zu
  Gebäudeplan-Bewohnern (`gp:<Name>`) stehen wie bisherige Notizen in `termine.json`.
* **Keine** Datenbank, keine Migration, keine Zugangsdaten in Sicherungen (API-Schlüssel liegen in der
  Windows-Anmeldeinformationsverwaltung).
* Echte Daten (Gebäudeplan, Klassenübersicht, Anreiselisten, Sicherungen) sind nie im Git-Repository.
