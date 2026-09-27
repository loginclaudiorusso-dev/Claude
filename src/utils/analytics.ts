/**
 * Pulse analytics engine – pure functions that turn normalised health data
 * into Readiness, Strain, Sleep and Body Battery scores and multi-day trends.
 * No React / native imports: everything here is unit-testable in Node.
 */
import type {
  DailyHealthData,
  DailyMetrics,
  DailySummary,
  DayKey,
  MetricTrend,
  Timestamp,
  TrendDirection,
  TrendPoint,
  TrendReport,
  TrendWindow,
  UserProfile,
} from '@/types/health';

import { computeBodyBattery } from './bodyBattery';
import { DEFAULT_RESTING_HEART_RATE, estimateMaxHeartRate } from './heartRate';
import { BASELINE_WINDOW_DAYS, computeBaselines, computeReadiness, nightlyHrv } from './readiness';
import { DEFAULT_SLEEP_NEED_MINUTES, analyzeSleep } from './sleep';
import { mean, linearSlope, round } from './stats';
import { recommendedStrainTarget, computeStrain } from './strain';
import { addDays, minutesBetween } from './time';

export * from './bodyBattery';
export * from './heartRate';
export * from './readiness';
export * from './sleep';
export * from './stats';
export * from './strain';
export * from './time';

export interface SummarizeOptions {
  /** Current time; limits the body-battery curve for today. */
  now?: Timestamp;
  /** Summary of the previous day – supplies prior strain, sleep debt and battery level. */
  previous?: DailySummary;
}

function dailyMetrics(day: DailyHealthData): DailyMetrics {
  return {
    hrvMs: nightlyHrv(day),
    restingHeartRate: day.restingHeartRate,
    steps: day.steps,
    activeEnergyKcal: day.activeEnergyKcal,
    vo2Max: day.vo2Max,
    respiratoryRate: day.respiratoryRate,
    workoutMinutes: round(day.workouts.reduce((acc, w) => acc + minutesBetween(w.start, w.end), 0)),
    workoutCount: day.workouts.length,
  };
}

/**
 * Computes every score for one day.
 * @param history Days *before* `day`, oldest first (only the last 7 are used for baselines).
 */
export function summarizeDay(
  day: DailyHealthData,
  history: readonly DailyHealthData[],
  profile: UserProfile = {},
  { now, previous }: SummarizeOptions = {},
): DailySummary {
  const baselines = computeBaselines(history);
  const maxHeartRate = estimateMaxHeartRate(profile, now === undefined ? undefined : new Date(now));
  const restingHeartRate =
    day.restingHeartRate ?? baselines.restingHeartRate?.mean ?? DEFAULT_RESTING_HEART_RATE;
  const hrOptions = { restingHeartRate, maxHeartRate, sex: profile.sex };

  const sleep = day.sleep
    ? analyzeSleep(day.sleep, {
        baseNeedMinutes: profile.sleepNeedMinutes ?? DEFAULT_SLEEP_NEED_MINUTES,
        priorStrain: previous?.strain.score,
        priorDebtMinutes: previous?.sleep?.debtMinutes,
      })
    : undefined;

  const readiness = computeReadiness(
    { hrvMs: nightlyHrv(day), restingHeartRate: day.restingHeartRate, sleepScore: sleep?.score },
    baselines,
  );

  return {
    date: day.date,
    metrics: dailyMetrics(day),
    baselines,
    readiness,
    strain: computeStrain(day, hrOptions),
    strainTarget: readiness ? recommendedStrainTarget(readiness.score) : undefined,
    sleep,
    bodyBattery: computeBodyBattery(day, {
      ...hrOptions,
      morningScore: readiness?.score ?? sleep?.score,
      previousLevel: previous?.bodyBattery?.currentLevel,
      until: now,
    }),
  };
}

/**
 * Summarises a whole history in chronological order, chaining each day's
 * result (strain → next night's sleep need, sleep debt, battery level).
 */
export function summarizeHistory(
  days: readonly DailyHealthData[],
  profile: UserProfile = {},
  now?: Timestamp,
): DailySummary[] {
  const sorted = [...days].sort((a, b) => a.date.localeCompare(b.date));
  const summaries: DailySummary[] = [];
  sorted.forEach((day, i) => {
    const prev = summaries[i - 1];
    const isConsecutive = prev !== undefined && addDays(prev.date, 1) === day.date;
    const windowStart = addDays(day.date, -BASELINE_WINDOW_DAYS);
    summaries.push(
      summarizeDay(
        day,
        sorted.slice(0, i).filter((d) => d.date >= windowStart),
        profile,
        {
          now,
          previous: isConsecutive ? prev : undefined,
        },
      ),
    );
  });
  return summaries;
}

// ---------------------------------------------------------------------------
// Trends
// ---------------------------------------------------------------------------

/** Relative change over the window below which a trend counts as flat. */
const FLAT_THRESHOLD = 0.03;

export function buildTrend(points: TrendPoint[]): MetricTrend {
  const values = points.map((p) => p.value);
  const present = values.filter((v): v is number => v !== null);
  const average = mean(present);
  const slope = linearSlope(values);

  let direction: TrendDirection = 'flat';
  if (slope !== null && average !== null && average !== 0) {
    const relChange = (slope * (points.length - 1)) / Math.abs(average);
    if (relChange > FLAT_THRESHOLD) direction = 'up';
    else if (relChange < -FLAT_THRESHOLD) direction = 'down';
  }

  const third = Math.max(1, Math.floor(points.length / 3));
  const head = mean(values.slice(0, third).filter((v): v is number => v !== null));
  const tail = mean(values.slice(-third).filter((v): v is number => v !== null));
  const changePct =
    head !== null && tail !== null && head !== 0
      ? round(((tail - head) / Math.abs(head)) * 100, 1)
      : null;

  return {
    points,
    average: average === null ? null : round(average, 1),
    slopePerDay: slope === null ? null : round(slope, 3),
    direction,
    changePct,
  };
}

/** Consecutive calendar days ending at `end`, oldest first. */
export function dayRange(end: DayKey, count: number): DayKey[] {
  return Array.from({ length: count }, (_, i) => addDays(end, i - count + 1));
}

/** Acute (last 7 days) to chronic (last 28 days) mean strain ratio. */
export function acuteChronicRatio(summaries: readonly DailySummary[], end: DayKey): number | null {
  const byDate = new Map(summaries.map((s) => [s.date, s.strain.score]));
  const collect = (n: number) =>
    dayRange(end, n)
      .map((d) => byDate.get(d))
      .filter((v): v is number => v !== undefined);
  const acute = collect(7);
  const chronic = collect(28);
  if (acute.length < 4 || chronic.length < 14) return null;
  const chronicMean = mean(chronic)!;
  return chronicMean === 0 ? null : round(mean(acute)! / chronicMean, 2);
}

/** Builds 7- or 30-day trend series ending at `end` (default: latest summary). */
export function buildTrendReport(
  summaries: readonly DailySummary[],
  window: TrendWindow,
  end: DayKey | undefined = summaries.at(-1)?.date,
): TrendReport | undefined {
  if (!end) return undefined;
  const byDate = new Map(summaries.map((s) => [s.date, s]));
  const days = dayRange(end, window);
  const series = (pick: (s: DailySummary) => number | undefined): MetricTrend =>
    buildTrend(
      days.map((date) => {
        const s = byDate.get(date);
        const v = s ? pick(s) : undefined;
        return { date, value: v === undefined ? null : v };
      }),
    );

  return {
    window,
    hrv: series((s) => s.metrics.hrvMs),
    restingHeartRate: series((s) => s.metrics.restingHeartRate),
    readiness: series((s) => s.readiness?.score),
    strain: series((s) => s.strain.score),
    sleepMinutes: series((s) => s.sleep?.totalSleepMinutes),
    deepSleepMinutes: series((s) => (s.sleep?.stageShare ? s.sleep.stages.deep : undefined)),
    remSleepMinutes: series((s) => (s.sleep?.stageShare ? s.sleep.stages.rem : undefined)),
    acuteChronicRatio: acuteChronicRatio(summaries, end),
  };
}
