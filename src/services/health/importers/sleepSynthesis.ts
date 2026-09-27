import type { SleepSegment, SleepStage } from '@/types/health';

import { hoursToMs } from './parseUtils';

export interface AggregatedSleep {
  start: number;
  end: number;
  /** Hours per stage. */
  deep?: number;
  core?: number;
  rem?: number;
  awake?: number;
  /** Total asleep hours (may include unstaged sleep). */
  asleep?: number;
}

/**
 * Exports that only contain nightly totals have no stage timing. We lay the
 * stages out back-to-back inside the session so totals, efficiency and the
 * session window are correct; the order within the night is not meaningful.
 */
export function synthesizeSleepSegments(agg: AggregatedSleep): SleepSegment[] {
  const { start, end } = agg;
  const staged = (agg.deep ?? 0) + (agg.core ?? 0) + (agg.rem ?? 0);
  const unspecified = Math.max(0, (agg.asleep ?? 0) - staged);
  const parts: [SleepStage, number][] = [
    ['deep', agg.deep ?? 0],
    ['core', agg.core ?? 0],
    ['rem', agg.rem ?? 0],
    ['asleep', unspecified],
    ['awake', agg.awake ?? 0],
  ];
  const segments: SleepSegment[] = [{ start, end, stage: 'inBed' }];
  let cursor = start;
  for (const [stage, hours] of parts) {
    if (hours <= 0) continue;
    const segEnd = Math.min(end, cursor + hoursToMs(hours));
    if (segEnd <= cursor) break;
    segments.push({ start: cursor, end: segEnd, stage });
    cursor = segEnd;
  }
  return segments;
}
