import type {
  DataSource,
  HeartRateSample,
  HrvSample,
  SleepSegment,
  Timestamp,
  Workout,
  WorkoutType,
} from '@/types/health';

/** A timestamped scalar (steps, kcal, VO₂max …). */
export interface ValueSample {
  timestamp: Timestamp;
  value: number;
}

/**
 * Source-agnostic intermediate format. HealthKit and every importer produce
 * this; `buildDailyHealthData` turns it into `DailyHealthData[]`.
 *
 * `steps` / energy samples are *additive* (summed per day); `restingHeartRate`,
 * `vo2Max` and `respiratoryRate` are averaged per day.
 */
export interface RawHealthRecords {
  source: DataSource;
  hrv: HrvSample[];
  heartRate: HeartRateSample[];
  restingHeartRate: ValueSample[];
  sleepSegments: SleepSegment[];
  steps: ValueSample[];
  activeEnergyKcal: ValueSample[];
  basalEnergyKcal: ValueSample[];
  vo2Max: ValueSample[];
  respiratoryRate: ValueSample[];
  workouts: Workout[];
}

export function emptyRecords(source: DataSource): RawHealthRecords {
  return {
    source,
    hrv: [],
    heartRate: [],
    restingHeartRate: [],
    sleepSegments: [],
    steps: [],
    activeEnergyKcal: [],
    basalEnergyKcal: [],
    vo2Max: [],
    respiratoryRate: [],
    workouts: [],
  };
}

export const KJ_PER_KCAL = 4.184;
export const METERS_PER_MILE = 1609.344;

/** Maps HealthKit / Health Auto Export activity names to our workout types. */
export function classifyWorkout(name: string | undefined): WorkoutType {
  const n = (name ?? '').toLowerCase().replace(/[\s_-]/g, '');
  if (/run|jog/.test(n)) return 'running';
  if (/cycl|bik|spin/.test(n)) return 'cycling';
  if (/hik/.test(n)) return 'hiking';
  if (/walk/.test(n)) return 'walking';
  if (/swim/.test(n)) return 'swimming';
  if (/highintensity|hiit|crosstraining|functional|circuit/.test(n)) return 'hiit';
  if (/strength|weight|core/.test(n)) return 'strength';
  if (/yoga|pilates|mindandbody|flexibility/.test(n)) return 'yoga';
  if (/row/.test(n)) return 'rowing';
  return 'other';
}
