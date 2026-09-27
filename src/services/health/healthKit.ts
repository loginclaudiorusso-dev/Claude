import { NativeModules, Platform } from 'react-native';
import type {
  HealthInputOptions,
  HealthKitPermissions,
  HealthValue,
  HKWorkoutQueriedSampleType,
} from 'react-native-health';

import type { DailyHealthData, DayKey, SleepStage } from '@/types/health';
import { HOUR_MS } from '@/utils/analytics';

import { buildDailyHealthData, dayRangeBounds } from './buildDays';
import {
  METERS_PER_MILE,
  classifyWorkout,
  emptyRecords,
  type RawHealthRecords,
  type ValueSample,
} from './raw';

/**
 * HealthKit adapter built on react-native-health. Only works in an iOS
 * development/production build – not in Expo Go, on Android or on web, where
 * `isHealthKitAvailable()` resolves to false.
 */

type AppleHealthKitModule = typeof import('react-native-health').default;

let module: AppleHealthKitModule | null | undefined;

function healthKit(): AppleHealthKitModule | null {
  if (module === undefined) {
    // react-native-health reads NativeModules.AppleHealthKit at import time (CommonJS
    // `module.exports`); guard so Android, web and Expo Go never evaluate it.
    module =
      Platform.OS === 'ios' && NativeModules.AppleHealthKit
        ? // eslint-disable-next-line @typescript-eslint/no-require-imports -- lazy native module
          (require('react-native-health') as AppleHealthKitModule)
        : null;
  }
  return module;
}

/** Read-only permissions. We never write to Health. */
const READ_PERMISSIONS = [
  'HeartRate',
  'RestingHeartRate',
  'HeartRateVariability',
  'SleepAnalysis',
  'StepCount',
  'ActiveEnergyBurned',
  'BasalEnergyBurned',
  'Vo2Max',
  'RespiratoryRate',
  'Workout',
] as const;

const PERMISSIONS = {
  permissions: { read: [...READ_PERMISSIONS], write: [] },
} as unknown as HealthKitPermissions;

function call<T>(
  fn: (options: HealthInputOptions, cb: (err: unknown, res: T) => void) => void,
  options: HealthInputOptions,
) {
  return new Promise<T>((resolve, reject) => {
    fn(options, (err, res) =>
      err ? reject(new Error(String((err as { message?: string })?.message ?? err))) : resolve(res),
    );
  });
}

export function isHealthKitAvailable(): Promise<boolean> {
  const hk = healthKit();
  if (!hk) return Promise.resolve(false);
  return new Promise((resolve) => hk.isAvailable((err, ok) => resolve(!err && ok)));
}

/**
 * Shows the system permission sheet (only the first time). HealthKit never
 * reveals whether read access was granted – an empty result is all we see –
 * so success here only means the sheet was handled.
 */
export function requestHealthKitPermissions(): Promise<void> {
  const hk = healthKit();
  if (!hk) return Promise.reject(new Error('HealthKit ist auf diesem Gerät nicht verfügbar.'));
  return new Promise((resolve, reject) =>
    hk.initHealthKit(PERMISSIONS, (err) => (err ? reject(new Error(String(err))) : resolve())),
  );
}

const SLEEP_STAGE_MAP: Record<string, SleepStage> = {
  INBED: 'inBed',
  ASLEEP: 'asleep',
  CORE: 'core',
  DEEP: 'deep',
  REM: 'rem',
  AWAKE: 'awake',
};

const ts = (iso: string) => new Date(iso).getTime();
const toValues = (rows: HealthValue[], factor = 1): ValueSample[] =>
  rows.map((r) => ({ timestamp: ts(r.startDate), value: r.value * factor }));

/** Fetches raw HealthKit samples for [from, to] (plus the evening before `from` for sleep). */
export async function fetchHealthKitRecords(from: DayKey, to: DayKey): Promise<RawHealthRecords> {
  const hk = healthKit();
  if (!hk) throw new Error('HealthKit ist auf diesem Gerät nicht verfügbar.');

  const { start, end } = dayRangeBounds(from, to);
  const range: HealthInputOptions = {
    startDate: new Date(start - 12 * HOUR_MS).toISOString(),
    endDate: new Date(end).toISOString(),
    ascending: true,
  };

  const [hr, hrv, rhr, sleep, steps, active, basal, vo2, resp, workouts] = await Promise.all([
    call<HealthValue[]>(hk.getHeartRateSamples, range),
    call<HealthValue[]>(hk.getHeartRateVariabilitySamples, range),
    call<HealthValue[]>(hk.getRestingHeartRateSamples, range),
    call<HealthValue[]>(hk.getSleepSamples, { ...range, limit: 5000 }),
    call<HealthValue[]>(hk.getDailyStepCountSamples, range),
    call<HealthValue[]>(hk.getActiveEnergyBurned, { ...range, period: 60 }),
    call<HealthValue[]>(hk.getBasalEnergyBurned, { ...range, period: 60 }),
    call<HealthValue[]>(hk.getVo2MaxSamples, range),
    call<HealthValue[]>(hk.getRespiratoryRateSamples, range),
    call<{ data: HKWorkoutQueriedSampleType[] }>(hk.getAnchoredWorkouts, {
      ...range,
      type: 'Workout',
    } as HealthInputOptions),
  ]);

  const records = emptyRecords('healthkit');
  records.heartRate = hr.map((r) => ({ timestamp: ts(r.startDate), bpm: r.value }));
  // react-native-health returns SDNN in seconds.
  records.hrv = hrv.map((r) => ({ timestamp: ts(r.startDate), sdnnMs: r.value * 1000 }));
  records.restingHeartRate = toValues(rhr);
  records.sleepSegments = sleep.flatMap((r) => {
    // The native bridge returns the stage as a string despite the `number` typing.
    const stage = SLEEP_STAGE_MAP[String(r.value).toUpperCase()];
    return stage ? [{ start: ts(r.startDate), end: ts(r.endDate), stage }] : [];
  });
  records.steps = toValues(steps);
  records.activeEnergyKcal = toValues(active);
  records.basalEnergyKcal = toValues(basal);
  records.vo2Max = toValues(vo2);
  records.respiratoryRate = toValues(resp);
  records.workouts = (workouts?.data ?? []).map((w) => ({
    id: w.id,
    type: classifyWorkout(w.activityName),
    name: w.activityName,
    start: ts(w.start),
    end: ts(w.end),
    activeEnergyKcal: w.calories ?? 0,
    distanceMeters: w.distance ? w.distance * METERS_PER_MILE : undefined,
  }));
  return records;
}

/** Loads and normalises HealthKit data for every day in [from, to]. */
export async function loadHealthKitDays(from: DayKey, to: DayKey): Promise<DailyHealthData[]> {
  const days = buildDailyHealthData(await fetchHealthKitRecords(from, to));
  return days.filter((d) => d.date >= from && d.date <= to);
}
