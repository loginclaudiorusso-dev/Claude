/**
 * Health data layer. The only entry point through which health data reaches
 * the app; everything is normalised to `DailyHealthData` (see src/types/health.ts).
 */
import type { DailyHealthData } from '@/types/health';

import { lookbackRange, mergeDays } from './buildDays';
import { generateDemoDays } from './demoData';
import { isHealthKitAvailable, loadHealthKitDays } from './healthKit';
import { pickAndImportHealthFile } from './importFile';
import { clearStoredDays, loadStoredDays, saveStoredDays } from './storage';

export { buildDailyHealthData, clusterSleepSessions, lookbackRange, mergeDays } from './buildDays';
export { generateDemoDays } from './demoData';
export { isHealthKitAvailable, requestHealthKitPermissions } from './healthKit';
export { UnsupportedImportError, parseHealthExport } from './importers';
export { pickAndImportHealthFile } from './importFile';
export type { RawHealthRecords } from './raw';

/** Days of history needed for 30-day trends plus a full 28-day chronic window. */
export const DEFAULT_LOOKBACK_DAYS = 45;

export type HealthDataMode = 'healthkit' | 'import' | 'demo';

/**
 * Loads days for the given mode:
 * - `healthkit`: fresh HealthKit query, merged into the local cache
 * - `import`: previously imported files from the local cache
 * - `demo`: generated data, never persisted
 */
export async function loadHealthDays(
  mode: HealthDataMode,
  lookbackDays = DEFAULT_LOOKBACK_DAYS,
): Promise<DailyHealthData[]> {
  if (mode === 'demo') return generateDemoDays(lookbackDays);

  if (mode === 'import') return loadStoredDays('import');

  const { from, to } = lookbackRange(lookbackDays);
  const merged = mergeDays(await loadStoredDays('healthkit'), await loadHealthKitDays(from, to));
  saveStoredDays('healthkit', merged);
  return merged;
}

/** Picks a file, merges it into the imported-days cache and returns all imported days. */
export async function importHealthFile(): Promise<{
  fileName: string;
  importedDays: number;
  days: DailyHealthData[];
} | null> {
  const result = await pickAndImportHealthFile();
  if (!result) return null;
  const days = mergeDays(await loadStoredDays('import'), result.days);
  saveStoredDays('import', days);
  return { fileName: result.fileName, importedDays: result.days.length, days };
}

/** Deletes all locally cached health data. */
export function deleteLocalHealthData(): void {
  clearStoredDays();
}

/** Picks the best available mode for this device. */
export async function detectDefaultMode(): Promise<HealthDataMode> {
  if (await isHealthKitAvailable()) return 'healthkit';
  return (await loadStoredDays('import')).length > 0 ? 'import' : 'demo';
}
