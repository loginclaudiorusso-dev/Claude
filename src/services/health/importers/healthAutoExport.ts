import { z } from 'zod';

import type { SleepStage } from '@/types/health';

import { classifyWorkout, emptyRecords, type RawHealthRecords, type ValueSample } from '../raw';
import { hoursToMs, parseDate, parseNumber, toKcal, toMeters } from './parseUtils';
import { synthesizeSleepSegments } from './sleepSynthesis';

/**
 * Importer for the JSON export of "Health Auto Export – JSON+CSV" (iOS).
 * Supports both export versions and aggregated as well as raw sleep data.
 * Schemas are deliberately loose: unknown metrics/fields are ignored.
 */

const quantity = z.union([
  z.number(),
  z.string(),
  z.object({ qty: z.unknown(), units: z.string().optional() }),
]);

const metricSchema = z.object({
  name: z.string(),
  units: z.string().optional(),
  data: z.array(z.record(z.string(), z.unknown())),
});

const workoutSchema = z
  .object({
    id: z.string().optional(),
    name: z.string().optional(),
    start: z.string(),
    end: z.string(),
    activeEnergyBurned: quantity.optional(),
    activeEnergy: quantity.optional(),
    avgHeartRate: quantity.optional(),
    maxHeartRate: quantity.optional(),
    heartRate: z
      .object({ avg: quantity.optional(), max: quantity.optional() })
      .partial()
      .optional(),
    distance: quantity.optional(),
  })
  .passthrough();

export const healthAutoExportSchema = z.object({
  data: z.object({
    metrics: z.array(metricSchema).default([]),
    workouts: z.array(workoutSchema).default([]),
  }),
});

export type HealthAutoExportJson = z.infer<typeof healthAutoExportSchema>;

export function isHealthAutoExportJson(json: unknown): boolean {
  return healthAutoExportSchema.safeParse(json).success;
}

const unitOf = (q: unknown): string | undefined =>
  q && typeof q === 'object' && 'units' in q ? String((q as { units: unknown }).units) : undefined;

const RAW_SLEEP_STAGE: Record<string, SleepStage> = {
  'in bed': 'inBed',
  inbed: 'inBed',
  asleep: 'asleep',
  core: 'core',
  deep: 'deep',
  rem: 'rem',
  awake: 'awake',
};

function valueSamples(
  rows: Record<string, unknown>[],
  transform: (v: number) => number = (v) => v,
): ValueSample[] {
  return rows.flatMap((row) => {
    const timestamp = parseDate(row.date);
    const value = parseNumber(row.qty ?? row.Avg ?? row.avg);
    return timestamp !== undefined && value !== undefined
      ? [{ timestamp, value: transform(value) }]
      : [];
  });
}

export function parseHealthAutoExport(json: unknown): RawHealthRecords {
  const parsed = healthAutoExportSchema.parse(json);
  const records = emptyRecords('import');

  for (const metric of parsed.data.metrics) {
    const rows = metric.data;
    switch (metric.name) {
      case 'heart_rate_variability':
        records.hrv.push(
          ...valueSamples(rows).map((s) => ({ timestamp: s.timestamp, sdnnMs: s.value })),
        );
        break;
      case 'heart_rate':
        records.heartRate.push(
          ...valueSamples(rows).map((s) => ({ timestamp: s.timestamp, bpm: s.value })),
        );
        break;
      case 'resting_heart_rate':
        records.restingHeartRate.push(...valueSamples(rows));
        break;
      case 'step_count':
        records.steps.push(...valueSamples(rows));
        break;
      case 'active_energy':
        records.activeEnergyKcal.push(...valueSamples(rows, (v) => toKcal(v, metric.units)));
        break;
      case 'basal_energy_burned':
        records.basalEnergyKcal.push(...valueSamples(rows, (v) => toKcal(v, metric.units)));
        break;
      case 'vo2_max':
        records.vo2Max.push(...valueSamples(rows));
        break;
      case 'respiratory_rate':
        records.respiratoryRate.push(...valueSamples(rows));
        break;
      case 'sleep_analysis':
        for (const row of rows) {
          // Raw (unaggregated) export: one row per stage segment.
          if (typeof row.value === 'string' && row.startDate) {
            const stage = RAW_SLEEP_STAGE[row.value.toLowerCase()];
            const start = parseDate(row.startDate);
            const end = parseDate(row.endDate);
            if (stage && start !== undefined && end !== undefined)
              records.sleepSegments.push({ start, end, stage });
            continue;
          }
          // Aggregated export: nightly totals in hours.
          const end = parseDate(row.sleepEnd ?? row.inBedEnd);
          const inBedStart = parseDate(row.inBedStart);
          const sleepStart = parseDate(row.sleepStart);
          const start = inBedStart ?? sleepStart;
          if (start === undefined || end === undefined) continue;
          const asleep = parseNumber(row.asleep) ?? parseNumber(row.totalSleep);
          records.sleepSegments.push(
            ...synthesizeSleepSegments({
              start,
              end: Math.max(end, start + hoursToMs(asleep ?? 0)),
              deep: parseNumber(row.deep),
              core: parseNumber(row.core),
              rem: parseNumber(row.rem),
              awake: parseNumber(row.awake),
              asleep,
            }),
          );
        }
        break;
      default:
        break;
    }
  }

  parsed.data.workouts.forEach((w, i) => {
    const start = parseDate(w.start);
    const end = parseDate(w.end);
    if (start === undefined || end === undefined) return;
    const energy = w.activeEnergyBurned ?? w.activeEnergy;
    const avgHr = parseNumber(w.avgHeartRate) ?? parseNumber(w.heartRate?.avg);
    const maxHr = parseNumber(w.maxHeartRate) ?? parseNumber(w.heartRate?.max);
    const distance = parseNumber(w.distance);
    records.workouts.push({
      id: w.id ?? `import-${start}-${i}`,
      type: classifyWorkout(w.name),
      name: w.name,
      start,
      end,
      activeEnergyKcal: energy === undefined ? 0 : toKcal(parseNumber(energy) ?? 0, unitOf(energy)),
      avgHeartRate: avgHr,
      maxHeartRate: maxHr,
      distanceMeters: distance === undefined ? undefined : toMeters(distance, unitOf(w.distance)),
    });
  });

  return records;
}
