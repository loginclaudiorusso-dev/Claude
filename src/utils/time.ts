import type { DayKey, Timestamp } from '@/types/health';

export const MINUTE_MS = 60_000;
export const HOUR_MS = 60 * MINUTE_MS;
export const DAY_MS = 24 * HOUR_MS;

const pad = (n: number) => String(n).padStart(2, '0');

/** Local calendar day for a timestamp. */
export function toDayKey(timestamp: Timestamp): DayKey {
  const d = new Date(timestamp);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Local midnight at the start of a day key. */
export function startOfDay(day: DayKey): Timestamp {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(y!, m! - 1, d!).getTime();
}

export function endOfDay(day: DayKey): Timestamp {
  return startOfDay(addDays(day, 1));
}

/** Calendar arithmetic that is safe across DST changes. */
export function addDays(day: DayKey, delta: number): DayKey {
  const [y, m, d] = day.split('-').map(Number);
  return toDayKey(new Date(y!, m! - 1, d! + delta, 12).getTime());
}

export function minutesBetween(start: Timestamp, end: Timestamp): number {
  return Math.max(0, (end - start) / MINUTE_MS);
}

/** Overlap of two intervals in minutes. */
export function overlapMinutes(
  aStart: Timestamp,
  aEnd: Timestamp,
  bStart: Timestamp,
  bEnd: Timestamp,
): number {
  return minutesBetween(Math.max(aStart, bStart), Math.min(aEnd, bEnd));
}
