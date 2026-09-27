import type Anthropic from '@anthropic-ai/sdk';
import { z } from 'zod';

import type { DailySummary, DayKey } from '@/types/health';
import { addDays, buildTrend, dayRange, mean, minutesBetween, round } from '@/utils/analytics';

import type { CoachContext } from './context';
import { buildCoachPayload } from './payload';

/**
 * Read-only tools the chat coach can call to look beyond today's snapshot.
 * They run locally over in-memory data – nothing leaves the device except the
 * tool results Claude asked for.
 */

const METRICS = {
  hrv: (s: DailySummary) => s.metrics.hrvMs,
  resting_heart_rate: (s: DailySummary) => s.metrics.restingHeartRate,
  readiness: (s: DailySummary) => s.readiness?.score,
  strain: (s: DailySummary) => s.strain.score,
  sleep_score: (s: DailySummary) => s.sleep?.score,
  sleep_minutes: (s: DailySummary) => s.sleep?.totalSleepMinutes,
  deep_sleep_minutes: (s: DailySummary) => (s.sleep?.stageShare ? s.sleep.stages.deep : undefined),
  rem_sleep_minutes: (s: DailySummary) => (s.sleep?.stageShare ? s.sleep.stages.rem : undefined),
  sleep_debt_minutes: (s: DailySummary) => s.sleep?.debtMinutes,
  body_battery_end: (s: DailySummary) => s.bodyBattery?.currentLevel,
  steps: (s: DailySummary) => s.metrics.steps,
  active_energy_kcal: (s: DailySummary) => s.metrics.activeEnergyKcal,
} as const;

type MetricName = keyof typeof METRICS;
const metricNames = Object.keys(METRICS) as [MetricName, ...MetricName[]];

const dateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
const daysSchema = z.number().int().min(1).max(90);

const inputSchemas = {
  get_day_summary: z.object({ date: dateSchema }),
  get_metric_series: z.object({ metric: z.enum(metricNames), days: daysSchema }),
  list_workouts: z.object({ days: daysSchema }),
  compare_after_training: z.object({ metric: z.enum(metricNames), days: daysSchema }),
};

export type CoachToolName = keyof typeof inputSchemas;

const metricDescription = `One of: ${metricNames.join(', ')}.`;

export const COACH_TOOLS: Anthropic.Beta.BetaTool[] = [
  {
    name: 'get_day_summary',
    description:
      'Full score snapshot (readiness, sleep, strain, body battery, workouts) for one calendar day. Use it for questions about a specific past day.',
    input_schema: {
      type: 'object',
      properties: { date: { type: 'string', description: 'Local date as YYYY-MM-DD.' } },
      required: ['date'],
      additionalProperties: false,
    },
    strict: true,
  },
  {
    name: 'get_metric_series',
    description: `Daily values of one metric for the last N days (ending today), with average, trend direction and change in %. ${metricDescription}`,
    input_schema: {
      type: 'object',
      properties: {
        metric: { type: 'string', enum: metricNames },
        days: { type: 'integer', description: 'Number of days, 1–90.' },
      },
      required: ['metric', 'days'],
      additionalProperties: false,
    },
    strict: true,
  },
  {
    name: 'list_workouts',
    description:
      "Workouts of the last N days with type, duration, avg HR, that day's strain, and the following night's sleep score and next-morning readiness.",
    input_schema: {
      type: 'object',
      properties: { days: { type: 'integer', description: 'Number of days, 1–90.' } },
      required: ['days'],
      additionalProperties: false,
    },
    strict: true,
  },
  {
    name: 'compare_after_training',
    description: `Compares a metric on the day AFTER training days vs. the day after rest days over the last N days (e.g. sleep or HRV after workouts). ${metricDescription}`,
    input_schema: {
      type: 'object',
      properties: {
        metric: { type: 'string', enum: metricNames },
        days: { type: 'integer', description: 'Number of days, 1–90.' },
      },
      required: ['metric', 'days'],
      additionalProperties: false,
    },
    strict: true,
  },
];

function latestDate(ctx: CoachContext): DayKey | undefined {
  return ctx.summaries.at(-1)?.date;
}

function summaryMap(ctx: CoachContext) {
  return new Map(ctx.summaries.map((s) => [s.date, s]));
}

const roundOrNull = (v: number | undefined) => (v === undefined ? null : round(v, 1));

function executeParsed<T extends CoachToolName>(
  name: T,
  input: z.infer<(typeof inputSchemas)[T]>,
  ctx: CoachContext,
): unknown {
  const end = latestDate(ctx);
  if (!end) return { error: 'Keine Gesundheitsdaten vorhanden.' };
  const byDate = summaryMap(ctx);

  switch (name) {
    case 'get_day_summary': {
      const { date } = input as z.infer<typeof inputSchemas.get_day_summary>;
      return buildCoachPayload(ctx, date) ?? { error: `Keine Daten für ${date}.` };
    }
    case 'get_metric_series': {
      const { metric, days } = input as z.infer<typeof inputSchemas.get_metric_series>;
      const pick = METRICS[metric];
      const trend = buildTrend(
        dayRange(end, days).map((date) => {
          const s = byDate.get(date);
          const v = s ? pick(s) : undefined;
          return { date, value: v === undefined ? null : round(v, 1) };
        }),
      );
      return { metric, ...trend };
    }
    case 'list_workouts': {
      const { days } = input as z.infer<typeof inputSchemas.list_workouts>;
      const from = addDays(end, -(days - 1));
      return ctx.days
        .filter((d) => d.date >= from && d.date <= end)
        .flatMap((d) =>
          d.workouts.map((w) => {
            const next = byDate.get(addDays(d.date, 1));
            return {
              date: d.date,
              type: w.name ?? w.type,
              durationMin: round(minutesBetween(w.start, w.end)),
              avgHeartRate: w.avgHeartRate ?? null,
              activeEnergyKcal: round(w.activeEnergyKcal),
              dayStrain: byDate.get(d.date)?.strain.score ?? null,
              nextNightSleepScore: next?.sleep?.score ?? null,
              nextMorningReadiness: next?.readiness?.score ?? null,
            };
          }),
        );
    }
    case 'compare_after_training': {
      const { metric, days } = input as z.infer<typeof inputSchemas.compare_after_training>;
      const pick = METRICS[metric];
      const trainingDays = new Set(
        ctx.days.filter((d) => d.workouts.length > 0).map((d) => d.date),
      );
      const afterTraining: number[] = [];
      const afterRest: number[] = [];
      for (const date of dayRange(end, days)) {
        const prev = addDays(date, -1);
        const s = byDate.get(date);
        const v = s ? pick(s) : undefined;
        if (v === undefined || !byDate.has(prev)) continue;
        (trainingDays.has(prev) ? afterTraining : afterRest).push(v);
      }
      const a = mean(afterTraining);
      const r = mean(afterRest);
      return {
        metric,
        afterTraining: { average: roundOrNull(a ?? undefined), days: afterTraining.length },
        afterRest: { average: roundOrNull(r ?? undefined), days: afterRest.length },
        differencePct:
          a !== null && r !== null && r !== 0 ? round(((a - r) / Math.abs(r)) * 100, 1) : null,
      };
    }
  }
  return { error: `Unbekanntes Tool: ${String(name)}` };
}

/**
 * Validates model-supplied input with zod before running a tool (eager input
 * streaming means the API no longer validates it) and returns a JSON string.
 */
export function executeCoachTool(
  name: string,
  input: unknown,
  ctx: CoachContext,
): { content: string; isError: boolean } {
  if (!(name in inputSchemas))
    return { content: JSON.stringify({ error: `Unknown tool ${name}` }), isError: true };
  const toolName = name as CoachToolName;
  const parsed = inputSchemas[toolName].safeParse(input);
  if (!parsed.success) {
    return {
      content: JSON.stringify({ INVALID_INPUT: parsed.error.issues.map((i) => i.message) }),
      isError: true,
    };
  }
  const result = executeParsed(toolName, parsed.data, ctx);
  const isError = typeof result === 'object' && result !== null && 'error' in result;
  return { content: JSON.stringify(result), isError };
}
