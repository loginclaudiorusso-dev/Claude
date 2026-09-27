import { File, Paths } from 'expo-file-system';

import type { CoachInsight } from '@/types/coach';
import type { DayKey } from '@/types/health';

/**
 * Keeps the last generated briefings next to the health cache (Documents
 * directory, not AsyncStorage) so the dashboard doesn't re-query Claude on
 * every launch. Keyed by day plus a fingerprint of the input data.
 */
interface CachedBriefing {
  fingerprint: string;
  insight: CoachInsight;
}

const MAX_ENTRIES = 14;
const file = () => new File(Paths.document, 'pulse-coach-briefings.v1.json');

async function readAll(): Promise<Record<DayKey, CachedBriefing>> {
  try {
    const f = file();
    if (!f.exists) return {};
    return JSON.parse(await f.text()) as Record<DayKey, CachedBriefing>;
  } catch {
    return {};
  }
}

export async function getCachedBriefing(
  date: DayKey,
  fingerprint: string,
): Promise<CoachInsight | null> {
  const entry = (await readAll())[date];
  return entry && entry.fingerprint === fingerprint ? entry.insight : null;
}

export async function cacheBriefing(
  date: DayKey,
  fingerprint: string,
  insight: CoachInsight,
): Promise<void> {
  const all = await readAll();
  all[date] = { fingerprint, insight };
  const kept = Object.fromEntries(
    Object.entries(all)
      .sort(([a], [b]) => b.localeCompare(a))
      .slice(0, MAX_ENTRIES),
  );
  try {
    const f = file();
    if (!f.exists) f.create();
    f.write(JSON.stringify(kept));
  } catch {
    // Caching is best effort (unavailable on web).
  }
}

export function clearBriefingCache(): void {
  try {
    const f = file();
    if (f.exists) f.delete();
  } catch {
    // Nothing cached.
  }
}
