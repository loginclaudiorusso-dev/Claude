import type {
  Baselines,
  DailyHealthData,
  MetricBaseline,
  ReadinessResult,
  RecoveryZone,
  ScoreConfidence,
} from '@/types/health';

import { totalSleepMinutes } from './sleep';
import { logistic, mean, round, standardDeviation, weightedAverage } from './stats';

export const BASELINE_WINDOW_DAYS = 7;
/** Minimum days before we trust a personal baseline. */
export const MIN_BASELINE_DAYS = 3;

/** Readiness weights. Missing inputs are dropped and weights renormalised. */
export const READINESS_WEIGHTS = { hrv: 0.5, restingHeartRate: 0.2, sleep: 0.3 } as const;

/**
 * Minimum SD used for z-scores so a very stable baseline does not turn tiny
 * day-to-day noise into extreme scores (≈ 8 % for ln HRV, 2 bpm for RHR).
 */
const LN_HRV_SD_FLOOR = 0.08;
const RHR_SD_FLOOR = 2;

/**
 * Nightly HRV: mean SDNN of samples recorded during the main sleep session
 * (most comparable, least affected by activity); falls back to all samples.
 */
export function nightlyHrv(day: DailyHealthData): number | undefined {
  const all = day.hrvSamples.filter((s) => s.sdnnMs > 0);
  const night = day.sleep
    ? all.filter((s) => s.timestamp >= day.sleep!.start && s.timestamp <= day.sleep!.end)
    : [];
  const values = (night.length > 0 ? night : all).map((s) => s.sdnnMs);
  return mean(values) ?? undefined;
}

function baseline(values: number[]): MetricBaseline | undefined {
  const m = mean(values);
  return m === null ? undefined : { mean: m, sd: standardDeviation(values), n: values.length };
}

/** Rolling baselines over the last `windowDays` days of `history` (excluding today). */
export function computeBaselines(
  history: readonly DailyHealthData[],
  windowDays = BASELINE_WINDOW_DAYS,
): Baselines {
  const window = history.slice(-windowDays);
  const hrv = window.map(nightlyHrv).filter((v): v is number => v !== undefined);
  const rhr = window
    .map((d) => d.restingHeartRate)
    .filter((v): v is number => v !== undefined && v > 0);
  const sleep = window.filter((d) => d.sleep).map((d) => totalSleepMinutes(d.sleep!));
  return {
    lnHrv: baseline(hrv.map(Math.log)),
    hrvMs: baseline(hrv),
    restingHeartRate: baseline(rhr),
    sleepMinutes: baseline(sleep),
  };
}

/**
 * Maps a z-score to 0–100. Calibrated so a "normal" day (z = 0) lands at ~62 %
 * (yellow/green border), +1 SD ≈ 87 %, −1 SD ≈ 29 %, −2 SD ≈ 9 %.
 */
export function zScoreToScore(z: number): number {
  return 100 * logistic(1.4 * z + 0.5);
}

export function recoveryZone(score: number): RecoveryZone {
  if (score >= 67) return 'green';
  if (score >= 34) return 'yellow';
  return 'red';
}

function confidenceFor(n: number): ScoreConfidence {
  if (n < MIN_BASELINE_DAYS) return 'calibrating';
  return n < 5 ? 'low' : 'high';
}

export interface ReadinessInput {
  hrvMs?: number;
  restingHeartRate?: number;
  /** 0–100 sleep score from `analyzeSleep`. */
  sleepScore?: number;
}

/**
 * Readiness / recovery (0–100 %):
 *  - HRV: z-score of ln(SDNN) vs. 7-day baseline (higher = better)
 *  - RHR: inverted z-score vs. 7-day baseline (lower = better)
 *  - Sleep: sleep score
 * Weighted 50 / 20 / 30. HRV and RHR only count once a baseline with at least
 * one prior day exists; confidence reflects how many days back it.
 */
export function computeReadiness(
  input: ReadinessInput,
  baselines: Baselines,
): ReadinessResult | undefined {
  const { hrvMs, restingHeartRate, sleepScore } = input;
  const lnBase = baselines.lnHrv;
  const rhrBase = baselines.restingHeartRate;

  let hrvScore: number | undefined;
  let hrvDeviationPct: number | undefined;
  if (hrvMs !== undefined && hrvMs > 0 && lnBase) {
    const z = (Math.log(hrvMs) - lnBase.mean) / Math.max(lnBase.sd, LN_HRV_SD_FLOOR);
    hrvScore = zScoreToScore(z);
    // Geometric mean = e^mean(ln) is the natural centre for log-normal HRV.
    hrvDeviationPct = (hrvMs / Math.exp(lnBase.mean) - 1) * 100;
  }

  let rhrScore: number | undefined;
  let rhrDeviation: number | undefined;
  if (restingHeartRate !== undefined && restingHeartRate > 0 && rhrBase) {
    rhrDeviation = restingHeartRate - rhrBase.mean;
    rhrScore = zScoreToScore(-rhrDeviation / Math.max(rhrBase.sd, RHR_SD_FLOOR));
  }

  const score = weightedAverage([
    { value: hrvScore, weight: READINESS_WEIGHTS.hrv },
    { value: rhrScore, weight: READINESS_WEIGHTS.restingHeartRate },
    { value: sleepScore, weight: READINESS_WEIGHTS.sleep },
  ]);
  if (score === null) return undefined;

  const baselineDays = Math.max(lnBase?.n ?? 0, rhrBase?.n ?? 0);
  const rounded = round(score);

  return {
    score: rounded,
    zone: recoveryZone(rounded),
    confidence:
      hrvScore === undefined && rhrScore === undefined
        ? 'calibrating'
        : confidenceFor(baselineDays),
    components: {
      hrv: hrvScore === undefined ? undefined : round(hrvScore),
      restingHeartRate: rhrScore === undefined ? undefined : round(rhrScore),
      sleep: sleepScore === undefined ? undefined : round(sleepScore),
    },
    hrvMs: hrvMs === undefined ? undefined : round(hrvMs, 1),
    hrvDeviationPct: hrvDeviationPct === undefined ? undefined : round(hrvDeviationPct, 1),
    restingHeartRate: restingHeartRate === undefined ? undefined : round(restingHeartRate, 1),
    restingHeartRateDeviationBpm: rhrDeviation === undefined ? undefined : round(rhrDeviation, 1),
  };
}
