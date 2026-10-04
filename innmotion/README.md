# INNmotion – Sport & Freizeit im Internat (Prototyp)

> Klickbarer Prototyp einer mobilen Web-App (PWA). Teilnehmende machen bei Sportangeboten, Challenges und Events mit, sammeln Punkte für ihr Standort-Team und messen sich fair mit den anderen Standorten.
> **Alle Daten sind erfunden.** Es gibt kein Backend und keine echten Personendaten. Alles liegt nur im Browser des jeweiligen Geräts.
> „INNmotion“ ist ein Arbeitstitel.

---

## Starten

Voraussetzung: Node.js 20 oder neuer.

```bash
cd innmotion
npm install && npm run dev
```

Dann im Browser **http://localhost:5173** öffnen. Am besten in den Entwicklertools die Handy-Ansicht wählen (z. B. iPhone 14, 390 × 844).

| Befehl | Zweck |
|---|---|
| `npm run dev` | Entwicklungsserver (localhost) |
| `npm run dev:https` | Wie oben, aber per HTTPS im WLAN erreichbar. Nötig, damit die **Kamera auf einem echten Handy** funktioniert. Beim ersten Aufruf die Zertifikatswarnung einmal bestätigen. |
| `npm run build && npm run preview` | Produktions-Build inkl. Service Worker unter http://localhost:4173 |
| `npm test` | Unit-Tests der Fachlogik (Punkte, Sperren, Liga, Turnier, Export) |
| `npm run typecheck` | TypeScript-Prüfung |
| `npm run check:screens` | Screenshots aller Screens bei 390 × 844 (hell + dunkel). Prüft auf horizontales Scrollen, abgeschnittene Texte, Konsolenfehler und Anfragen an Drittanbieter. Der Dev-Server muss laufen. |
| `npm run check:checkin` | End-to-End-Test: echter QR-Scan über eine simulierte Kamera, 3-Stunden-Sperre, manuelle Code-Eingabe |
| `npm run check:pwa` | Prüft am Produktions-Build die Installierbarkeit, den Service Worker und den Offline-Start (`npm run preview` muss laufen) |

### Als App installieren

* **Android/Chrome:** Menü → „App installieren“
* **iPhone/Safari:** Teilen → „Zum Home-Bildschirm“

Die App startet dann im Vollbild mit eigenem Icon und funktioniert auch offline.

---

## Demo-Zugänge

Es gibt kein Login. Oben im **Profil** steht ein **Rollenwechsler**. Dort lässt sich auch jede andere Demo-Person auswählen.

| Rolle | Demo-Person | Was man zeigen kann |
|---|---|---|
| **Teilnehmende** | **Kalle**, Team Goslar | Start mit Wochenring, Einchecken, Challenges, Events mit Warteliste, Liga, Abzeichen, Wünsch dir was, Kurzumfrage, Meine Daten |
| **Betreuung** | **Sandra (Freizeit)**, Goslar | Rotierender QR-Code im Vollbild, Teilnahmen des Tages korrigieren oder nachtragen, Event anlegen, Turnier-Ergebnisse eintragen, Ankündigung senden, Ideen als „wird umgesetzt“ markieren |
| **Leitung** | **Leitung Internat** | Dashboard mit Kennzahlen und Verläufen, CSV-Export, Umfrage-Auswertung, Verwaltung (Orte und Belegung, Challenges, Saisons, Regeln), Datenschutz, Druckvorlage für QR-Aushänge |

**Demo zurücksetzen:** Profil → „Demo zurücksetzen“. Das erzeugt frische Demo-Daten passend zum heutigen Datum.

### Vorschlag für den Demo-Ablauf (ca. 5 Minuten)

1. **Teilnehmende (Kalle):** Auf dem Start-Bildschirm stehen 2 von 3 Aktivitäten. Dann **Einchecken → Code eingeben**.
2. Den Code holen: Rolle **Betreuung** → Reiter **Code**. Dort läuft gerade der „Offene Badminton-Treff“. Zurück zu Kalle, Code eingeben.
   Ergebnis: Animation, **Wochenziel geschafft**, **neues Angebot** und das **neue Abzeichen „Allrounder“**.
3. Gleich nochmal einchecken: Die **Sperre** greift („Der nächste Check-in an diesem Ort geht ab …“).
4. **Liga:** Gewertet wird *pro Kopf* (Punkte pro aktivem Teilnehmenden). Die Gesamtpunkte stehen klein darunter. Daran sieht man, dass der größte Standort nicht automatisch gewinnt.
5. **Liga → Einzel:** Kalle ist nicht in der Rangliste (Opt-in). Er sieht nur „obere Hälfte deines Teams“.
6. **Leitung → Dashboard:** Teilnahmequote je Standort, 12-Wochen-Verlauf, CSV-Export.

Mit zwei Geräten (Handy + Laptop mit `npm run dev:https`) lässt sich auch der echte QR-Scan zeigen. Weil die Daten nur lokal liegen, braucht jedes Gerät dafür denselben Stand. Für die Live-Demo daher den QR-Code im Vollbild auf dem Laptop zeigen und mit dem Handy auf demselben Gerät scannen, oder den Code eintippen.

---

## Grundprinzipien – so umgesetzt

| Prinzip | Umsetzung |
|---|---|
| **Mitmachen zählt mehr als Leistung** | Punkte gibt es nur für Teilnahme, Ausprobieren und gemeinsames Einchecken, nie für Leistung. Ein Turniersieg bringt ein Abzeichen, aber keine Extrapunkte. |
| **Niemand wird bloßgestellt** | Die Einzel-Rangliste ist Opt-in und zeigt nur die Top 10. Ohne Opt-in gibt es eine positive Einordnung („obere Hälfte“, „du bist dabei“). Es gibt keine letzten Plätze. |
| **Fairer Standortvergleich** | Liga = Punkte ÷ aktive Teilnehmende der Saison. Team-Challenge-Ziele richten sich nach der Größe des Standorts. |
| **Datensparsam** | Nur Spitznamen. Keine Gesundheits- oder Körperdaten, kein GPS. Die Kamera liest nur den Code. Umfrage-Antworten werden ohne Personenbezug gespeichert. Exporte enthalten nur aggregierte Werte. |
| **Einfach** | Ein Tap von „Start“ zum Scanner. Touch-Flächen mindestens 48 px, Du-Ansprache, einfache Sprache. |

### Punkte und Schutz gegen Mehrfach-Punkte

| Aktion | Punkte |
|---|---|
| Check-in Fitnessraum / Halle | 10 |
| Event-Teilnahme | laut Event (Standard 15, Turnier 20) |
| Erstes Mal ein neues Angebot | +5 |
| Zu zweit eingecheckt (innerhalb von 10 Min. am selben Ort) | +5 für beide |
| Wochenziel erreicht (Standard: 3 Aktivitäten) | +10 |

* Pro Ort bzw. Event höchstens **ein Check-in je 3 Stunden**
* **Tagesobergrenze** für Punkte (Standard 40). Die Aktivität zählt trotzdem für Wochenziel und Serie.
* **Raum-Codes wechseln täglich.** Der QR-Code auf dem Handy der Betreuung **rotiert zusätzlich alle 30 Sekunden**, damit Fotos davon schnell ungültig werden.
* **Event-Codes** gelten nur von 30 Minuten vor Beginn bis zum Ende.
* Codes gelten nur am eigenen Standort.

Wochenziel und Tagesobergrenze stellt die Leitung unter *Verwaltung → Regeln* ein.

---

## Technik und Struktur

**Technik:** Vite, React 19, TypeScript, Tailwind CSS 4, React Router, Zustand (localStorage), `vite-plugin-pwa`, `jsQR` (QR-Erkennung im Browser) und `qrcode` (QR-Erzeugung).
Die Schrift *Inter* ist lokal eingebunden (`@fontsource-variable`), die Diagramme sind schlanke eigene SVGs.
Es gibt **keine** CDNs, Tracker oder Analytics. Das prüft `check:screens` bzw. `check:pwa` automatisch.

```
innmotion/
├─ src/
│  ├─ domain/          Reine Fachlogik ohne React – mit Unit-Tests
│  │   ├─ checkin.ts     Codes prüfen, Sperren, Punkte, Tagesobergrenze, gemeinsames Einchecken
│  │   ├─ codes.ts       Tages-, Event- und rotierende QR-Codes
│  │   ├─ league.ts      Standort-Liga (pro aktivem TN), Saisonverlauf, Opt-in-Rangliste, Team-Einordnung
│  │   ├─ challenges.ts  Fortschritt Woche / Team / Saison
│  │   ├─ badges.ts      Abzeichen (aus Daten berechnet)
│  │   ├─ tournament.ts  Gruppen, K.-o.-Baum mit Freilosen, automatische Tabelle
│  │   ├─ stats.ts       Dashboard-Kennzahlen, Umfrage-Auswertung, CSV
│  │   └─ types.ts       Datenmodell
│  ├─ services/
│  │   ├─ api.ts         Service-Schnittstelle (die UI kennt nur diese)
│  │   ├─ hooks.ts       Lese-Hooks für die Screens
│  │   └─ mock/          Prototyp-Implementierung: Zustand + localStorage
│  ├─ seed/generate.ts  Demo-Daten-Generator (deterministisch, relativ zum heutigen Datum)
│  ├─ screens/          participant/ · staff/ · lead/ · shared/
│  ├─ components/       UI-Bausteine, Diagramme, QR-Scanner, Turnier-Ansicht
│  └─ theme/            Design-Tokens hell/dunkel, Teamfarben (auf Farbfehlsichtigkeit geprüft)
├─ scripts/            Screenshot-, E2E- und PWA-Prüfungen, Icon-Generator
└─ public/             App-Icons (Platzhalter)
```

**Backend später anbinden:** Alle Änderungen laufen über `InnmotionApi` (`src/services/api.ts`). Für den echten Betrieb kommt eine zweite Implementierung dazu (z. B. `services/supabase/`). Die Lese-Hooks in `services/hooks.ts` werden dann auf einen Query-Cache umgestellt. Die Screens selbst bleiben unverändert. Die Fachlogik in `domain/` lässt sich serverseitig weiterverwenden, etwa in einer Edge Function für die Check-in-Prüfung.

### Demo-Daten

* 3 Standorte: Goslar (16 TN), Weser-Ems (18 TN), Bad Pyrmont (12 TN). Je 2 Orte (Fitnessraum, Sporthalle) mit pflegbarer Belegung.
* 12 Wochen Check-in-Historie mit realistischen Schwankungen (Ferienwoche, unterschiedlich aktive Personen). Das deckt die geforderten 8 Wochen ab und füllt den 12-Wochen-Verlauf im Dashboard.
* 6 laufende Challenges (plus eine kommende), 5 kommende Events plus ein gerade laufendes, ein laufendes Tischtennis-Turnier (Gruppenphase fast fertig) und ein abgeschlossener Darts-Cup.
* 10 Ideen bei „Wünsch dir was“, 1 abgeschlossene Kurzumfrage (34 Antworten), 1 laufende Umfrage.
* Je eine Demo-Person pro Rolle (siehe oben). Eine archivierte Vorsaison.

---

## Was für den echten Betrieb fehlt

**Zugang und Sicherheit**
* **Login und Rollen:** z. B. Einladungscode pro Standort bzw. Magic Link; Rollen Teilnehmende / Betreuung / Leitung serverseitig durchsetzen (Row-Level-Security)
* **Check-in-Prüfung auf dem Server:** Sperren, Tagesobergrenze und Code-Prüfung serverseitig; Code-Geheimnis nur auf dem Server; Missbrauchserkennung

**Hosting und Daten**
* **EU-Hosting** (z. B. Supabase in Frankfurt oder ein eigener Server) mit Auftragsverarbeitungsvertrag, Backups und Verschlüsselung
* **Echte Web-Push-Benachrichtigungen** (VAPID). Im Prototyp sind sie simuliert.
* **Automatische Löschung** als geplanter Job (Einstellung ist vorhanden); Export der eigenen Daten (Art. 15/20 DSGVO)

**Datenschutz und Mitbestimmung**
* **Datenschutz-Folgenabschätzung (DSFA)**, Verzeichnis von Verarbeitungstätigkeiten, Datenschutzhinweise in einfacher Sprache, Einwilligungstexte (Opt-in Rangliste, Benachrichtigungen)
* **Abstimmung mit Betriebsrat und Datenschutzbeauftragter** – insbesondere zu Auswertungen und zur Rolle der Betreuung (keine Leistungs- oder Verhaltenskontrolle von Beschäftigten)
* Klare Regel: Teilnahme ist **freiwillig** und hat keinen Einfluss auf die Maßnahme

**Barrierefreiheit und Qualität**
* **Barrierefreiheitsprüfung** nach BITV 2.0 / WCAG 2.1 AA mit echten Nutzerinnen und Nutzern (Screenreader, große Schrift, eingeschränkte Motorik); Texte in Leichter Sprache prüfen lassen
* Test auf älteren und günstigen Android-Geräten; Kamera-Erkennung bei schlechtem Licht
* Echte App-Icons und Gestaltung nach CI; finaler Name

**Betrieb und Pflege**
* Zuständigkeiten: Wer pflegt Events, Challenges, Saisons, Belegung? Schulung der Betreuung
* Aushänge: QR-Codes täglich drucken oder Tablet am Eingang (rotierender Code)
* Support-Kontakt, Fehler-Monitoring (datensparsam, EU), Updates und Sicherheits-Patches
* Laufende Kosten für Hosting und Wartung klären, Verantwortliche für Inhalte benennen
* Auswertung nach 3 bis 6 Monaten: Steigt die Teilnahmequote? Kurzumfrage-Verlauf
