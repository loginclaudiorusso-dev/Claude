# Pulse – Health Analytics & Claude Coach

Expo / React Native App (iPhone & iPad) zur automatisierten Auswertung von Apple-Health-Daten – Erholung, Belastung, Schlaf und Body Battery – mit einem Claude-basierten Performance Coach.

## Stack

| Bereich | Technologie |
|---|---|
| Framework | Expo SDK 57, React Native 0.86, React 19.2, TypeScript (strict) |
| Navigation | Expo Router (typed routes), native `UITabBarController` Tabs (Liquid Glass, iPad Sidebar) |
| UI | `expo-blur` (Frosted Glass), `expo-symbols` (SF Symbols), `expo-haptics`, `react-native-reanimated` 4 (Spring Physics) |
| Charts | `victory-native` (Skia) + `react-native-svg` für Ringe |
| Health Data | `react-native-health` (HealthKit) · JSON/CSV-Import (`expo-document-picker`, `papaparse`) |
| AI | `@anthropic-ai/sdk`, Standardmodell `claude-opus-5` (per `EXPO_PUBLIC_CLAUDE_MODEL` änderbar) |
| State / Storage | `zustand`, `@react-native-async-storage/async-storage`, `expo-secure-store` (Keychain für API-Key) |
| Validation | `zod` (Import-Parsing, Coach-Antworten) |

## Projektstruktur

```
src/
├── app/                      # Expo Router – jede Datei ist ein Screen
│   ├── _layout.tsx           # Root Stack, Dark Theme, GestureHandler
│   ├── index.tsx             # Redirect → /dashboard
│   └── (tabs)/
│       ├── _layout.tsx       # Native Tabs (SF Symbols, iPad-Sidebar)
│       ├── dashboard/        # Heute: Erholung, Belastung, Schlaf, Body Battery, Briefing
│       ├── trends/           # 7/30-Tage Trends: HRV, Schlafarchitektur, Trainingslast
│       ├── coach/            # AI Coach Chat & Insights
│       └── settings/         # API-Key, HealthKit-Berechtigungen, Import
├── components/
│   ├── navigation/           # Gemeinsame Header-Optionen (Large Title + Blur)
│   └── ui/                   # GlassCard, Screen, PlaceholderCard …
├── config/                   # Modell- & Keychain-Konstanten
├── hooks/                    # useResponsiveLayout (Size Classes compact/regular)
├── test/                     # Synthetische Test-Fixtures
├── theme/                    # Farben (HIG Dark), Typografie (SF Pro), Radii, Springs
├── types/
│   ├── health.ts             # Samples, Tagesdaten, Profile, Baselines, Scores, Trends
│   └── coach.ts              # Coach-Payload (JSON an Claude), Insights, Chat
└── utils/                    # Reine Scoring-Engine (ohne React/Native-Imports)
    ├── analytics.ts          # Fassade: summarizeDay/History, Trend-Reports, ACWR
    ├── readiness.ts          # Erholung 0–100 %
    ├── strain.ts             # Belastung 0–21
    ├── sleep.ts              # Schlafanalyse, Bedarf, Schlafschuld
    ├── bodyBattery.ts        # Energieverlauf über den Tag
    ├── heartRate.ts          # HFmax, HRR, Zonen, Banister-TRIMP
    ├── stats.ts / time.ts    # Statistik- & Kalender-Helfer
    └── __tests__/            # Jest-Tests
```

Folgende Module kommen in den nächsten Schritten hinzu:

- `src/services/health/` – HealthKit-Adapter + JSON/CSV-Import
- `src/services/claudeCoach.ts` – Claude-Coach (System-Prompt, Daily Briefing, Chat)

## Scoring-Modelle

| Score | Modell |
|---|---|
| **Readiness (0–100 %)** | 50 % HRV + 20 % Ruhepuls + 30 % Schlaf. HRV: z-Score von ln(SDNN, nur Nachtwerte) gegen die 7-Tage-Baseline; Ruhepuls: invertierter z-Score. Abbildung `100 · logistic(1.4 z + 0.5)` → normaler Tag ≈ 62 %, +1 SD ≈ 87 %, −1 SD ≈ 29 %. Fehlende Eingaben werden herausgerechnet; unter 3 Baseline-Tagen gilt der Score als „calibrating“. Zonen: ≥ 67 grün, ≥ 34 gelb, sonst rot. |
| **Strain (0–21)** | Banister-TRIMP über alle HF-Samples oberhalb 30 % Herzfrequenzreserve (Karvonen, HFmax nach Tanaka), dann `21 · (1 − e^(−TRIMP/110))`. Ersatzweise Workouts mit Durchschnittspuls + aktive Kalorien, zuletzt nur aktive Kalorien. Liefert Minuten in Zone 1–5 und eine Zielspanne passend zur Readiness. |
| **Schlaf** | Phasen (Tief/REM/Kern/Wach) mit Deduplizierung überlappender Quellen. Bedarf = Basis (8 h) + 6 min je Strain-Punkt über 10 + 25 % der Schlafschuld (max. 60 min). Schlafschuld zerfällt täglich um 15 %. Score = 60 % Bedarf erreicht + 15 % Effizienz + 25 % Architektur (Tief-/REM-Minuten gegen 15 % / 20 % des Bedarfs). |
| **Body Battery (0–100)** | Morgenwert `10 + 0.9 · Readiness`; danach minütlicher Abbau: 2,1 Punkte/h im Wachzustand, fast keiner bei ruhigem Puls, plus 0,18 × TRIMP bei Aktivität. Der Endwert des Vortags zeichnet das nächtliche Aufladen. |
| **Trends** | 7/30-Tage-Reihen (Lücken = `null`), Regressions-Steigung, Richtung (±3 %-Schwelle), Veränderung erstes vs. letztes Drittel, Acute:Chronic-Ratio (7 d / 28 d Strain). |

## Entwicklung

```bash
npm install
npm run typecheck      # tsc --noEmit
npm run lint           # expo lint
npm test               # Jest (Scoring-Engine)
npx expo run:ios       # Development Build (HealthKit benötigt nativen Build, kein Expo Go)
```

HealthKit funktioniert nur in einem Development Build auf echtem Gerät oder Simulator mit Health-Daten. Das `react-native-health` Config-Plugin setzt Entitlements und Info.plist-Texte automatisch (`app.json`). `ios/` und `android/` werden per Continuous Native Generation erzeugt und nicht eingecheckt.

## Sicherheit

Der Anthropic API-Key wird ausschließlich in `expo-secure-store` (iOS Keychain) abgelegt und nie im Quellcode, in AsyncStorage oder in `EXPO_PUBLIC_*`-Variablen gespeichert (diese werden in das JS-Bundle eingebettet). Für Produktions-Apps mit vielen Nutzern empfiehlt sich zusätzlich ein eigener Backend-Proxy statt Client-seitiger Keys.
