import type {
  BiologicalSex,
  DailyHealthData,
  HeartRateSample,
  StrainLevel,
  StrainResult,
  StrainTarget,
  Workout,
  ZoneMinutes,
} from '@/types/health';

import { banisterTrimpPerMinute, heartRateReserve, heartRateZone } from './heartRate';
import { clamp, round } from './stats';
import { MINUTE_MS, minutesBetween } from './time';

export const MAX_STRAIN = 21;
/**
 * Scale of the saturating curve strain = 21 × (1 − e^(−TRIMP / k)).
 * k = 110 ⇒ TRIMP 30 ≈ 5, 100 ≈ 12.5 (hard hour), 250 ≈ 18.9.
 */
export const STRAIN_TRIMP_SCALE = 110;
/** Load only accumulates above 30 % heart-rate reserve (light activity and up). */
export const LOAD_THRESHOLD_HRR = 0.3;
/** Longest gap a single HR sample may represent (Apple Watch samples every ~5 min at rest). */
const MAX_SAMPLE_GAP_MS = 10 * MINUTE_MS;
/** Minimum samples for a heart-rate-based calculation. */
const MIN_HR_SAMPLES = 24;
/** TRIMP-equivalents per kcal when only energy data is available. */
const TRIMP_PER_ACTIVE_KCAL = 0.15;
const TRIMP_PER_NON_WORKOUT_KCAL = 0.08;

export function trimpToStrain(trimp: number): number {
  return round(MAX_STRAIN * (1 - Math.exp(-Math.max(0, trimp) / STRAIN_TRIMP_SCALE)), 1);
}

export function strainLevel(strain: number): StrainLevel {
  if (strain >= 18) return 'allOut';
  if (strain >= 14) return 'high';
  if (strain >= 10) return 'moderate';
  return 'light';
}

/**
 * Recommended strain range for a readiness score: ≈ 4 at 0 %, 11 at 50 %,
 * 18 at 100 %, ± 1.5.
 */
export function recommendedStrainTarget(readinessScore: number): StrainTarget {
  const center = 4 + 0.14 * clamp(readinessScore, 0, 100);
  return {
    min: round(clamp(center - 1.5, 0, MAX_STRAIN), 1),
    max: round(clamp(center + 1.5, 0, MAX_STRAIN), 1),
  };
}

const emptyZones = (): ZoneMinutes => ({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 });

function inWorkout(ts: number, workouts: readonly Workout[]): boolean {
  return workouts.some((w) => ts >= w.start && ts <= w.end);
}

export interface StrainOptions {
  restingHeartRate: number;
  maxHeartRate: number;
  sex?: BiologicalSex;
}

/**
 * Integrates Banister TRIMP over the day's heart-rate samples. Each sample
 * represents the time until the next sample (capped at 10 min).
 */
export function heartRateLoad(
  samples: readonly HeartRateSample[],
  workouts: readonly Workout[],
  { restingHeartRate, maxHeartRate, sex }: StrainOptions,
): { trimp: number; workoutTrimp: number; zoneMinutes: ZoneMinutes } {
  const sorted = [...samples].sort((a, b) => a.timestamp - b.timestamp);
  const zoneMinutes = emptyZones();
  let trimp = 0;
  let workoutTrimp = 0;

  sorted.forEach((sample, i) => {
    const next = sorted[i + 1];
    const gap = next ? Math.min(next.timestamp - sample.timestamp, MAX_SAMPLE_GAP_MS) : MINUTE_MS;
    const minutes = gap / MINUTE_MS;
    const hrr = heartRateReserve(sample.bpm, restingHeartRate, maxHeartRate);
    const zone = heartRateZone(hrr);
    if (zone) zoneMinutes[zone] += minutes;
    if (hrr >= LOAD_THRESHOLD_HRR) {
      const load = banisterTrimpPerMinute(hrr, sex) * minutes;
      trimp += load;
      if (inWorkout(sample.timestamp, workouts)) workoutTrimp += load;
    }
  });

  return { trimp, workoutTrimp, zoneMinutes };
}

/**
 * Day strain (0–21). Uses, in order of preference:
 *  1. continuous heart-rate samples (Banister TRIMP, HR zones),
 *  2. workouts with average HR + remaining active energy,
 *  3. active energy only.
 */
export function computeStrain(day: DailyHealthData, options: StrainOptions): StrainResult {
  let trimp: number;
  let workoutTrimp = 0;
  let zoneMinutes = emptyZones();
  let method: StrainResult['method'];

  if (day.heartRateSamples.length >= MIN_HR_SAMPLES) {
    ({ trimp, workoutTrimp, zoneMinutes } = heartRateLoad(
      day.heartRateSamples,
      day.workouts,
      options,
    ));
    method = 'heartRate';
  } else if (day.workouts.some((w) => w.avgHeartRate)) {
    let workoutKcal = 0;
    for (const w of day.workouts) {
      workoutKcal += w.activeEnergyKcal;
      const minutes = minutesBetween(w.start, w.end);
      if (w.avgHeartRate) {
        const hrr = heartRateReserve(
          w.avgHeartRate,
          options.restingHeartRate,
          options.maxHeartRate,
        );
        workoutTrimp += banisterTrimpPerMinute(hrr, options.sex) * minutes;
        const zone = heartRateZone(hrr);
        if (zone) zoneMinutes[zone] += minutes;
      } else {
        workoutTrimp += w.activeEnergyKcal * TRIMP_PER_ACTIVE_KCAL;
      }
    }
    trimp =
      workoutTrimp + Math.max(0, day.activeEnergyKcal - workoutKcal) * TRIMP_PER_NON_WORKOUT_KCAL;
    method = 'workoutEstimate';
  } else {
    trimp = day.activeEnergyKcal * TRIMP_PER_ACTIVE_KCAL;
    workoutTrimp = day.workouts.reduce(
      (acc, w) => acc + w.activeEnergyKcal * TRIMP_PER_ACTIVE_KCAL,
      0,
    );
    method = 'energyEstimate';
  }

  const score = trimpToStrain(trimp);
  return {
    score,
    level: strainLevel(score),
    trimp: round(trimp, 1),
    workoutTrimp: round(workoutTrimp, 1),
    zoneMinutes: {
      1: round(zoneMinutes[1]),
      2: round(zoneMinutes[2]),
      3: round(zoneMinutes[3]),
      4: round(zoneMinutes[4]),
      5: round(zoneMinutes[5]),
    },
    method,
  };
}
