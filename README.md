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
└── theme/                    # Farben (HIG Dark), Typografie (SF Pro), Radii, Springs
```

Folgende Module kommen in den nächsten Schritten hinzu:

- `src/types/health.ts` – Typdefinitionen für Health- und Coaching-Daten
- `src/utils/analytics.ts` – Readiness-, Strain-, Schlaf- und Body-Battery-Algorithmen
- `src/services/health/` – HealthKit-Adapter + JSON/CSV-Import
- `src/services/claudeCoach.ts` – Claude-Coach (System-Prompt, Daily Briefing, Chat)

## Entwicklung

```bash
npm install
npm run typecheck      # tsc --noEmit
npm run lint           # expo lint
npx expo run:ios       # Development Build (HealthKit benötigt nativen Build, kein Expo Go)
```

HealthKit funktioniert nur in einem Development Build auf echtem Gerät oder Simulator mit Health-Daten. Das `react-native-health` Config-Plugin setzt Entitlements und Info.plist-Texte automatisch (`app.json`). `ios/` und `android/` werden per Continuous Native Generation erzeugt und nicht eingecheckt.

## Sicherheit

Der Anthropic API-Key wird ausschließlich in `expo-secure-store` (iOS Keychain) abgelegt und nie im Quellcode, in AsyncStorage oder in `EXPO_PUBLIC_*`-Variablen gespeichert (diese werden in das JS-Bundle eingebettet). Für Produktions-Apps mit vielen Nutzern empfiehlt sich zusätzlich ein eigener Backend-Proxy statt Client-seitiger Keys.
