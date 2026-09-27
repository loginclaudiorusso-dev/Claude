@AGENTS.md

## Project: Pulse – Health Analytics & Claude Coach

- Scoring logic lives in `src/utils/` and must stay pure (no React / native imports) so it is unit-testable.
- Health data enters only through `src/services/health/` (HealthKit or JSON/CSV import) and is normalised to the types in `src/types/health.ts`.
- The Anthropic API key is stored exclusively in `expo-secure-store` (Keychain) – never in AsyncStorage, source code or logs.
- Design tokens live in `src/theme/`; do not hard-code colours or radii in screens.
- Sleep-stage colours in `src/theme/colors.ts` were validated for colour-vision deficiency in the order deep → REM → core → awake; keep that stacking order and re-validate before changing them.
