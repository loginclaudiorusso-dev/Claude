import type { CoachDailyPayload } from '@/types/coach';
import type { DayKey } from '@/types/health';
import { addDays, buildTrendReport, minutesBetween, round } from '@/utils/analytics';

import type { CoachContext } from './context';

const hours = (minutes: number) => round(minutes / 60, 1);
const orNull = <T>(v: T | undefined): T | null => (v === undefined ? null : v);

/**
 * Compact JSON snapshot of one day for the model. Pure and deterministic, so
 * identical data yields identical prompts (good for caching and tests).
 * Returns null if no summary exists for the date.
 */
export function buildCoachPayload(ctx: CoachContext, date?: DayKey): CoachDailyPayload | null {
  const target = date ?? ctx.summaries.at(-1)?.date;
  if (!target) return null;
  const summary = ctx.summaries.find((s) => s.date === target);
  if (!summary) return null;
  const day = ctx.days.find((d) => d.date === target);
  const yesterday = ctx.summaries.find((s) => s.date === addDays(target, -1));
  const trends = buildTrendReport(ctx.summaries, 7, target);
  const { readiness, sleep, strain, bodyBattery } = summary;

  return {
    date: target,
    readiness: readiness
      ? {
          score: readiness.score,
          zone: readiness.zone,
          confidence: readiness.confidence,
          hrvMs: orNull(readiness.hrvMs),
          hrvDeviationPct: orNull(readiness.hrvDeviationPct),
          restingHeartRate: orNull(readiness.restingHeartRate),
          restingHeartRateDeviationBpm: orNull(readiness.restingHeartRateDeviationBpm),
        }
      : null,
    sleep: sleep
      ? {
          totalHours: hours(sleep.totalSleepMinutes),
          needHours: hours(sleep.sleepNeedMinutes),
          performancePct: sleep.performancePct,
          efficiencyPct: round(sleep.efficiency * 100),
          deepPct: sleep.stageShare ? round(sleep.stageShare.deep * 100) : null,
          remPct: sleep.stageShare ? round(sleep.stageShare.rem * 100) : null,
          debtHours: hours(sleep.debtMinutes),
          score: sleep.score,
        }
      : null,
    strain: {
      yesterday: yesterday ? yesterday.strain.score : null,
      today: strain.score,
      level: strain.level,
      targetRange: summary.strainTarget
        ? [summary.strainTarget.min, summary.strainTarget.max]
        : null,
      zoneMinutes: {
        z1: strain.zoneMinutes[1],
        z2: strain.zoneMinutes[2],
        z3: strain.zoneMinutes[3],
        z4: strain.zoneMinutes[4],
        z5: strain.zoneMinutes[5],
      },
    },
    bodyBattery: bodyBattery
      ? { current: round(bodyBattery.currentLevel), startOfDay: round(bodyBattery.startLevel) }
      : null,
    activity: {
      steps: summary.metrics.steps,
      activeEnergyKcal: summary.metrics.activeEnergyKcal,
      workouts: (day?.workouts ?? []).map((w) => ({
        type: w.name ?? w.type,
        durationMin: round(minutesBetween(w.start, w.end)),
        activeEnergyKcal: round(w.activeEnergyKcal),
        avgHeartRate: orNull(w.avgHeartRate),
      })),
      vo2Max: orNull(summary.metrics.vo2Max),
    },
    trends7d: {
      hrv: trends?.hrv.direction ?? 'flat',
      restingHeartRate: trends?.restingHeartRate.direction ?? 'flat',
      sleep: trends?.sleepMinutes.direction ?? 'flat',
      acuteChronicRatio: trends?.acuteChronicRatio ?? null,
    },
  };
}
