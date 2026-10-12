# Rückweg: von 6.0 zurück zur Version 5.17.0

Version 6.0 überarbeitet die Oberfläche (Zimmer- und Personenkarte, mehrere Fenster, Datensicherung).
Der Stand davor – **5.17.0, so wie er beim Nutzer lief** – ist mehrfach gesichert und jederzeit wieder
herstellbar, ohne Code von Hand zu rekonstruieren.

## 1. Wo der Ausgangsstand liegt

| Was | Wo | Inhalt |
|---|---|---|
| Git-Branch (GitHub) | `backup/v5.17.0-vor-ui-overhaul` → Commit `2072131` | Code 5.17.0 (ohne echte Daten) |
| Git-Branch (GitHub) | `claude/bold-keller-8jch4a` → Commit `2072131` | unverändert, derselbe Stand |
| Git-Tag (nur lokal) | `v5.17.0-sicherung` → Commit `2072131` | Tags lassen sich aus der Arbeitsumgebung nicht pushen |
| Zip-Paket | `INNternat_v5.17.0_Sicherung.zip` (wurde mitgeliefert) | komplettes Programm 5.17.0 wie zuletzt ausgeliefert |

Der Overhaul liegt auf dem Branch **`claude/ui-overhaul-v6`** (Basis `2072131`).

## 2. Schnellster Rückweg (lokal, ohne Git) – 3 Schritte

1. Dashboard beenden (auch im Infobereich unten rechts: Rechtsklick auf das Symbol → **Beenden**).
2. `INNternat_v5.17.0_Sicherung.zip` in den Programmordner
   `C:\Users\claudio.russo\Documents\GitClaude\INNternat` entpacken und alles überschreiben.
3. `Start.bat` starten – in der Seitenleiste steht wieder **v5.17.0**.

Die Arbeitsdaten bleiben dabei erhalten: Die Zips enthalten keine Zuweisungen, Termine, Notizen oder
Einstellungen, und 6.0 hat kein Datenformat verändert. Übrig bleiben nur harmlose Reste:
neue Programmdateien von 6.0 (z. B. `belegung/ui/zimmerkarte.py`, werden von 5.17.0 nicht benutzt) und der
Ordner `Sicherungen/`. Notizen zu Zimmern bzw. zu Bewohnern aus dem Gebäudeplan zeigt 5.17.0 weiter als
Wiedervorlage unter Termine an (nur „Öffnen“ führt dort nicht zur Karte).

**Ganz sauber (optional):** Ordner `INNternat` in `INNternat_v6` umbenennen, neuen Ordner `INNternat`
anlegen, 5.17.0-Zip hinein entpacken und aus `INNternat_v6` die Arbeitsdaten zurückkopieren: alle `*.json`
im Hauptordner, die Ordner `importe`, `Gebaeudeplan`, `UWT`, `Listen` und – falls gewünscht – `Sicherungen`.

## 3. Arbeitsdaten zurückholen (unabhängig von der Version)

* **In 6.0:** Einstellungen → Datensicherung → Sicherung wählen → **Wiederherstellen …**
  Der aktuelle Stand wird vorher automatisch gesichert („vor Wiederherstellung“).
* **Von Hand (jede Version):** Dashboard beenden, aus `Sicherungen/<Datum>_<Uhrzeit>_v…/` die Dateien in den
  Programmordner kopieren (Unterordner `importe` mit).
* 6.0 legt beim ersten Start automatisch eine Sicherung **„vor Update“** an.

**Empfehlung vor jedem Update:** den ganzen Ordner `INNternat` kopieren (z. B. `INNternat_Sicherung_2026-10-12`).

## 4. Rückweg mit Git

```bash
git fetch origin
# Ausgangsstand ansehen bzw. damit weiterarbeiten (verändert nichts am Overhaul)
git switch -c arbeit-v517 origin/backup/v5.17.0-vor-ui-overhaul
# oder lokal über den Tag
git switch -c arbeit-v517 v5.17.0-sicherung

# Overhaul komplett zurücknehmen, ohne Verlauf umzuschreiben (Revert-Commits auf dem Overhaul-Branch)
git switch claude/ui-overhaul-v6
git revert --no-edit 2072131..HEAD

# nur einzelne Schritte zurücknehmen (neuester zuerst, siehe Abhängigkeiten unten)
git revert --no-edit <commit>
```

Kein `git reset --hard`, kein Force-Push nötig – der Ausgangsstand bleibt auf seinen Branches unverändert.

## 5. Die Schritte des Overhauls (je ein Commit auf `claude/ui-overhaul-v6`)

| Commit | Art | Inhalt | hängt ab von |
|---|---|---|---|
| `178baef` | Daten/Infrastruktur | Datensicherung beim Start (`belegung/datensicherung.py`), `.gitignore` | – |
| `4098d18` | fachlich | Bewohner-Schlüssel für Gebäudeplan/UWT, Notizen auch für Zimmer (`zimmerplan.py`, `suche.py`) | – |
| `61d77a8` | UI | Zimmer- und Personenkarte, Suche/Termine öffnen alle Bewohner (`ui/zimmerkarte.py`, `ui/notizen.py`) | `4098d18` |
| `c5ec862` | UI | Mehrere Fenster, einklappbare Hinweise, Zuteilen-Leiste (`ui/fenster.py`, `ui/basis.py`) | `61d77a8` |
| `c19bbb3` | UI | Datensicherung in den Einstellungen | `178baef` |
| `db37470` | Doku | Version 6.0.0, README, ROLLBACK.md | – |
| `49819ad` | Daten | erste Sicherung einer neuen Version heißt „vor Update“ | `178baef` |

## 6. Was sich geändert hat – und was nicht

* **Unverändert:** Abhängigkeiten (`requirements.txt`), Start (`Start.bat`), Datenformate, Planungsregeln,
  Import von Gebäudeplan/Anreiselisten/UWT, Statistik und Prognose.
* **Neu im Datenordner:** Ordner `Sicherungen/` (nur Kopien). Notizen zu Zimmern (`zimmer:<ID>`) und zu
  Gebäudeplan-Bewohnern (`gp:<Name>`) stehen wie bisherige Notizen in `termine.json`.
* **Keine** Datenbank, keine Migration, keine Zugangsdaten in Sicherungen (API-Schlüssel liegen in der
  Windows-Anmeldeinformationsverwaltung).
* Echte Daten (Gebäudeplan, Klassenübersicht, Anreiselisten, Sicherungen) sind nie im Git-Repository.
