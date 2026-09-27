import type {
  BiologicalSex,
  BodyBatteryPoint,
  BodyBatteryResult,
  DailyHealthData,
  HeartRateSample,
  Timestamp,
} from '@/types/health';

import { banisterTrimpPerMinute, heartRateReserve } from './heartRate';
import { clamp, round } from './stats';
import { HOUR_MS, MINUTE_MS, endOfDay, startOfDay } from './time';

/** Drain per awake minute without meaningful activity (~2.1 points/hour). */
export const BASE_DRAIN_PER_MINUTE = 0.035;
/** Drain per minute when HR confirms calm rest (HRR < 15 %). */
export const REST_DRAIN_PER_MINUTE = 0.01;
/** Battery points drained per TRIMP unit (1 h at 70 % HRR ≈ −19, at 87 % ≈ −32). */
export const DRAIN_PER_TRIMP = 0.18;
const REST_HRR = 0.15;
const ACTIVE_HRR = 0.3;
const SAMPLE_VALID_MS = 15 * MINUTE_MS;
const POINT_INTERVAL_MIN = 15;
const DEFAULT_WAKE_HOUR = 7;

/** Morning charge derived from readiness: 0 % → 10, 100 % → 100. */
export function startLevelFromReadiness(readiness: number): number {
  return clamp(10 + 0.9 * readiness, 5, 100);
}

export interface BodyBatteryOptions {
  restingHeartRate: number;
  maxHeartRate: number;
  sex?: BiologicalSex;
  /** Readiness (preferred) or sleep score that sets the morning level. */
  morningScore?: number;
  /** Previous day's end level – draws the overnight recharge segment. */
  previousLevel?: number;
  /** Evaluate until this moment (defaults to end of day). */
  until?: Timestamp;
}

/** Returns the most recent sample within 15 min before `t` (samples sorted asc). */
function makeHrLookup(samples: readonly HeartRateSample[]) {
  const sorted = [...samples].sort((a, b) => a.timestamp - b.timestamp);
  let idx = 0;
  return (t: Timestamp): number | undefined => {
    while (idx + 1 < sorted.length && sorted[idx + 1]!.timestamp <= t) idx++;
    const s = sorted[idx];
    return s && s.timestamp <= t && t - s.timestamp <= SAMPLE_VALID_MS ? s.bpm : undefined;
  };
}

/**
 * Energy level (0–100) across the waking day. The morning level comes from
 * readiness; afterwards every minute drains the battery by a base rate plus an
 * activity term proportional to Banister TRIMP. Calm, low-HR periods drain
 * only slightly. Missing HR is treated as ordinary awake time.
 */
export function computeBodyBattery(
  day: DailyHealthData,
  options: BodyBatteryOptions,
): BodyBatteryResult {
  const dayStart = startOfDay(day.date);
  const dayEnd = endOfDay(day.date);
  const wake =
    day.sleep && day.sleep.end >= dayStart ? day.sleep.end : dayStart + DEFAULT_WAKE_HOUR * HOUR_MS;
  const until = clamp(options.until ?? dayEnd, wake, dayEnd);
  const startLevel = round(
    options.morningScore === undefined ? 65 : startLevelFromReadiness(options.morningScore),
    1,
  );

  const points: BodyBatteryPoint[] = [];
  if (options.previousLevel !== undefined && day.sleep) {
    points.push({ timestamp: day.sleep.start, level: round(options.previousLevel, 1) });
  }
  points.push({ timestamp: wake, level: startLevel });

  const hrAt = makeHrLookup(day.heartRateSamples);
  let level = startLevel;
  let drained = 0;
  let minutes = 0;

  for (let t = wake; t < until; t += MINUTE_MS) {
    const bpm = hrAt(t);
    let drain = BASE_DRAIN_PER_MINUTE;
    if (bpm !== undefined) {
      const hrr = heartRateReserve(bpm, options.restingHeartRate, options.maxHeartRate);
      if (hrr < REST_HRR) drain = REST_DRAIN_PER_MINUTE;
      else if (hrr >= ACTIVE_HRR)
        drain += DRAIN_PER_TRIMP * banisterTrimpPerMinute(hrr, options.sex);
    }
    const next = Math.max(0, level - drain);
    drained += level - next;
    level = next;
    minutes++;
    if (minutes % POINT_INTERVAL_MIN === 0)
      points.push({ timestamp: t + MINUTE_MS, level: round(level, 1) });
  }
  if (minutes % POINT_INTERVAL_MIN !== 0) points.push({ timestamp: until, level: round(level, 1) });

  const levels = points.map((p) => p.level);
  return {
    points,
    startLevel,
    currentLevel: round(level, 1),
    charged:
      options.previousLevel === undefined
        ? 0
        : round(Math.max(0, startLevel - options.previousLevel), 1),
    drained: round(drained, 1),
    min: Math.min(...levels),
    max: Math.max(...levels),
  };
}
