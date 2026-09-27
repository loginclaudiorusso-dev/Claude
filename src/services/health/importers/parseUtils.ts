import { HOUR_MS } from '@/utils/analytics';

import { KJ_PER_KCAL } from '../raw';

/**
 * Parses Health Auto Export dates ("2024-02-06 07:04:00 +0100"), ISO strings
 * and plain dates ("2024-02-06", interpreted as local midnight).
 *
 * Health Auto Export stamps daily buckets with local midnight plus the phone's
 * UTC offset. We keep the *wall-clock* time and drop the offset so a bucket
 * always lands on the calendar day the user saw, even if the device's time
 * zone differs from the export's (travel, simulator, CI).
 */
export function parseDate(input: unknown): number | undefined {
  if (typeof input === 'number') return Number.isFinite(input) ? input : undefined;
  if (typeof input !== 'string' || input.trim() === '') return undefined;
  const s = input.trim();
  const hae = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?\s*[+-]\d{2}:?\d{2}$/.exec(
    s,
  );
  if (hae) {
    const [, y, mo, d, h, mi, sec] = hae.map(Number);
    return new Date(y!, mo! - 1, d!, h!, mi!, sec || 0).getTime();
  }
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (dateOnly)
    return new Date(Number(dateOnly[1]), Number(dateOnly[2]) - 1, Number(dateOnly[3])).getTime();
  const localDateTime = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/.exec(s);
  if (localDateTime) {
    const [, y, mo, d, h, mi, sec] = localDateTime.map(Number);
    return new Date(y!, mo! - 1, d!, h!, mi!, sec ?? 0).getTime();
  }
  const parsed = Date.parse(s);
  return Number.isNaN(parsed) ? undefined : parsed;
}

/** Parses numbers, accepting a decimal comma ("1,5") and `{ qty }` objects. */
export function parseNumber(input: unknown): number | undefined {
  if (typeof input === 'number') return Number.isFinite(input) ? input : undefined;
  if (input && typeof input === 'object' && 'qty' in input)
    return parseNumber((input as { qty: unknown }).qty);
  if (typeof input !== 'string') return undefined;
  const s = input.trim();
  if (s === '') return undefined;
  const normalised = s.includes('.') ? s.replace(/,/g, '') : s.replace(',', '.');
  const n = Number(normalised);
  return Number.isFinite(n) ? n : undefined;
}

/** Converts energy to kcal based on a unit label ("kJ", "kcal", "Cal"). */
export function toKcal(value: number, unit: string | undefined): number {
  return unit && /kj/i.test(unit) ? value / KJ_PER_KCAL : value;
}

/** Converts a distance to metres based on a unit label ("km", "mi", "m"). */
export function toMeters(value: number, unit: string | undefined): number {
  const u = (unit ?? 'km').toLowerCase();
  if (u.startsWith('mi')) return value * 1609.344;
  if (u === 'm') return value;
  return value * 1000;
}

export const hoursToMs = (hours: number) => hours * HOUR_MS;
