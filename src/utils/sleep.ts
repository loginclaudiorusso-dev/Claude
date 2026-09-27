import type { SleepAnalysis, SleepSegment, SleepSession, SleepStageMinutes } from '@/types/health';

import { clamp, normalize, round, weightedAverage } from './stats';
import { minutesBetween } from './time';

export const DEFAULT_SLEEP_NEED_MINUTES = 480;
/** Share of yesterday's debt that is still owed tonight (debt fades over ~1 week). */
export const SLEEP_DEBT_DECAY = 0.85;
/** Cap so one bad week does not dominate the need forever. */
export const MAX_SLEEP_DEBT_MINUTES = 12 * 60;
/** Reference shares of the sleep need for a well-structured night (adult norms). */
const DEEP_SHARE_TARGET = 0.15;
const REM_SHARE_TARGET = 0.2;

/**
 * Removes the `inBed` envelope and clips overlapping stage segments (multiple
 * sources can report the same minutes) so each minute is counted once.
 */
function cleanStageSegments(segments: readonly SleepSegment[]): SleepSegment[] {
  const staged = segments
    .filter((s) => s.stage !== 'inBed' && s.end > s.start)
    .sort((a, b) => a.start - b.start);
  const result: SleepSegment[] = [];
  let cursor = -Infinity;
  for (const seg of staged) {
    const start = Math.max(seg.start, cursor);
    if (start >= seg.end) continue;
    result.push({ ...seg, start });
    cursor = seg.end;
  }
  return result;
}

export function sleepStageMinutes(session: SleepSession): SleepStageMinutes {
  const stages: SleepStageMinutes = { awake: 0, core: 0, deep: 0, rem: 0, unspecified: 0 };
  for (const seg of cleanStageSegments(session.segments)) {
    const mins = minutesBetween(seg.start, seg.end);
    if (seg.stage === 'asleep') stages.unspecified += mins;
    else if (seg.stage !== 'inBed') stages[seg.stage] += mins;
  }
  return stages;
}

/** Total minutes asleep; falls back to time in bed if only `inBed` data exists. */
export function totalSleepMinutes(session: SleepSession): number {
  const s = sleepStageMinutes(session);
  const asleep = s.core + s.deep + s.rem + s.unspecified;
  return asleep > 0 ? asleep : minutesBetween(session.start, session.end) - s.awake;
}

/**
 * Tonight's sleep need = personal base need
 *   + strain adjustment (4 min per strain point above 10 the day before, ≤ 44 min)
 *   + debt repayment (20 % of the running debt, max 45 min).
 * Worst case ≈ base + 1.5 h, which stays achievable.
 */
export function calculateSleepNeed(
  baseNeedMinutes: number,
  priorStrain = 0,
  priorDebtMinutes = 0,
): number {
  const strainAdjustment = Math.max(0, priorStrain - 10) * 4;
  const debtRepayment = Math.min(priorDebtMinutes * 0.2, 45);
  return baseNeedMinutes + strainAdjustment + debtRepayment;
}

/**
 * Rolling sleep debt with exponential decay: yesterday's debt × 0.85 plus
 * tonight's deficit versus (base need + strain adjustment). Surplus sleep pays
 * debt back; the result never drops below zero.
 */
export function updateSleepDebt(
  priorDebtMinutes: number,
  sleptMinutes: number,
  needWithoutRepaymentMinutes: number,
): number {
  const next = priorDebtMinutes * SLEEP_DEBT_DECAY + (needWithoutRepaymentMinutes - sleptMinutes);
  return clamp(next, 0, MAX_SLEEP_DEBT_MINUTES);
}

export interface SleepAnalysisOptions {
  baseNeedMinutes?: number;
  /** Strain score of the day before this night. */
  priorStrain?: number;
  /** Debt carried in from the previous night's analysis. */
  priorDebtMinutes?: number;
}

/**
 * Sleep score (0–100) = weighted blend of
 *   60 % performance (actual ÷ need),
 *   15 % efficiency (75 % → 0, 95 % → 100),
 *   25 % architecture (deep ≥ 15 %, REM ≥ 20 % of the sleep *need* in minutes,
 *        so a short night cannot score well on proportions alone).
 * Components that cannot be measured are dropped and the weights renormalised.
 */
export function analyzeSleep(
  session: SleepSession,
  options: SleepAnalysisOptions = {},
): SleepAnalysis {
  const {
    baseNeedMinutes = DEFAULT_SLEEP_NEED_MINUTES,
    priorStrain = 0,
    priorDebtMinutes = 0,
  } = options;

  const stages = sleepStageMinutes(session);
  const staged = stages.core + stages.deep + stages.rem;
  const hasSleepData = staged + stages.unspecified > 0;
  const timeInBed = minutesBetween(session.start, session.end);
  const totalSleep = totalSleepMinutes(session);
  const efficiency = timeInBed > 0 ? clamp(totalSleep / timeInBed, 0, 1) : 0;

  const stageShare =
    staged > 0 && stages.unspecified < staged
      ? {
          core: stages.core / totalSleep,
          deep: stages.deep / totalSleep,
          rem: stages.rem / totalSleep,
        }
      : undefined;

  const need = calculateSleepNeed(baseNeedMinutes, priorStrain, priorDebtMinutes);
  const performancePct = need > 0 ? clamp((totalSleep / need) * 100, 0, 100) : 100;

  const architecture = stageShare
    ? ((Math.min(1, stages.deep / (need * DEEP_SHARE_TARGET)) +
        Math.min(1, stages.rem / (need * REM_SHARE_TARGET))) /
        2) *
      100
    : undefined;

  const score =
    weightedAverage([
      { value: performancePct, weight: 0.6 },
      { value: hasSleepData ? normalize(efficiency, 0.75, 0.95) * 100 : undefined, weight: 0.15 },
      { value: architecture, weight: 0.25 },
    ]) ?? 0;

  const needWithoutRepayment = calculateSleepNeed(baseNeedMinutes, priorStrain, 0);

  return {
    timeInBedMinutes: round(timeInBed),
    totalSleepMinutes: round(totalSleep),
    stages: {
      awake: round(stages.awake),
      core: round(stages.core),
      deep: round(stages.deep),
      rem: round(stages.rem),
      unspecified: round(stages.unspecified),
    },
    stageShare,
    efficiency: round(efficiency, 3),
    sleepNeedMinutes: round(need),
    performancePct: round(performancePct),
    debtMinutes: round(updateSleepDebt(priorDebtMinutes, totalSleep, needWithoutRepayment)),
    score: round(score),
    bedtime: session.start,
    wakeTime: session.end,
  };
}
