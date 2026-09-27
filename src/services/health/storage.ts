import { File, Paths } from 'expo-file-system';

import type { DailyHealthData } from '@/types/health';

/**
 * Local cache of normalised days in the app's Documents directory (sandboxed,
 * encrypted at rest by iOS Data Protection, excluded from other apps).
 * Health data is never written to AsyncStorage.
 */
export type StorageBucket = 'healthkit' | 'import';

interface StoredDays {
  version: 1;
  savedAt: number;
  days: DailyHealthData[];
}

const storeFile = (bucket: StorageBucket) =>
  new File(Paths.document, `pulse-health-${bucket}.v1.json`);

export async function loadStoredDays(bucket: StorageBucket): Promise<DailyHealthData[]> {
  try {
    const file = storeFile(bucket);
    if (!file.exists) return [];
    const parsed = JSON.parse(await file.text()) as Partial<StoredDays>;
    return parsed.version === 1 && Array.isArray(parsed.days) ? parsed.days : [];
  } catch {
    return [];
  }
}

export function saveStoredDays(bucket: StorageBucket, days: readonly DailyHealthData[]): void {
  const file = storeFile(bucket);
  if (!file.exists) file.create();
  const payload: StoredDays = { version: 1, savedAt: Date.now(), days: [...days] };
  file.write(JSON.stringify(payload));
}

export function clearStoredDays(): void {
  for (const bucket of ['healthkit', 'import'] as const) {
    const file = storeFile(bucket);
    if (file.exists) file.delete();
  }
}
