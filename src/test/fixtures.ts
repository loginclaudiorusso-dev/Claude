import type {
  DailyHealthData,
  DayKey,
  HeartRateSample,
  SleepSegment,
  Workout,
} from '@/types/health';

import { HOUR_MS, MINUTE_MS, addDays, startOfDay } from '@/utils/time';

export interface DayOptions {
  hrv?: number;
  rhr?: number;
  sleepHours?: number;
  /** Adds a workout from 18:00 at this HR for `workoutMinutes`. */
  workoutHr?: number;
  workoutMinutes?: number;
  activeEnergyKcal?: number;
  withHeartRate?: boolean;
  staged?: boolean;
}

/**
 * Synthetic day: bedtime 23:00 the evening before, wake after `sleepHours`,
 * resting HR samples every 5 min while awake, optional evening workout.
 */
export function makeDay(date: DayKey, o: DayOptions = {}): DailyHealthData {
  const {
    hrv = 50,
    rhr = 55,
    sleepHours = 8,
    workoutMinutes = 60,
    activeEnergyKcal = 450,
    staged = true,
  } = o;
  const midnight = startOfDay(date);
  const bed = midnight - HOUR_MS;
  const wake = bed + sleepHours * HOUR_MS;

  // Staging: 5 % awake, 17 % deep, 22 % REM, rest core – in 90-min cycles.
  const segments: SleepSegment[] = [{ start: bed, end: wake, stage: 'inBed' }];
  const cycle = 90 * MINUTE_MS;
  for (let t = bed; t < wake; t += cycle) {
    const end = Math.min(t + cycle, wake);
    const len = end - t;
    if (!staged) {
      segments.push({ start: t, end, stage: 'asleep' });
      continue;
    }
    const cuts: [number, SleepSegment['stage']][] = [
      [0.05, 'awake'],
      [0.17, 'deep'],
      [0.56, 'core'],
      [0.22, 'rem'],
    ];
    let cursor = t;
    for (const [share, stage] of cuts) {
      const segEnd = cursor + len * share;
      segments.push({ start: cursor, end: segEnd, stage });
      cursor = segEnd;
    }
  }

  const workouts: Workout[] = [];
  const hr: HeartRateSample[] = [];
  const workoutStart = midnight + 18 * HOUR_MS;
  const workoutEnd = workoutStart + workoutMinutes * MINUTE_MS;
  if (o.workoutHr) {
    workouts.push({
      id: `${date}-w`,
      type: 'running',
      start: workoutStart,
      end: workoutEnd,
      activeEnergyKcal: workoutMinutes * 11,
      avgHeartRate: o.workoutHr,
    });
  }
  if (o.withHeartRate) {
    for (let t = wake; t < midnight + 24 * HOUR_MS; t += 5 * MINUTE_MS) {
      const inWorkout = o.workoutHr && t >= workoutStart && t < workoutEnd;
      if (inWorkout) {
        for (let s = t; s < t + 5 * MINUTE_MS; s += MINUTE_MS)
          hr.push({ timestamp: s, bpm: o.workoutHr! });
      } else {
        hr.push({ timestamp: t, bpm: rhr + 10 });
      }
    }
  }

  return {
    date,
    source: 'demo',
    hrvSamples: [
      { timestamp: bed + 2 * HOUR_MS, sdnnMs: hrv },
      { timestamp: bed + 5 * HOUR_MS, sdnnMs: hrv },
      // Daytime sample that must be ignored in favour of nightly values.
      { timestamp: midnight + 14 * HOUR_MS, sdnnMs: hrv * 0.5 },
    ],
    restingHeartRate: rhr,
    heartRateSamples: hr,
    sleep: { start: bed, end: wake, segments },
    steps: 9000,
    activeEnergyKcal,
    workouts,
  };
}

/** `count` consecutive days ending at `end` built with the same options. */
export function makeHistory(end: DayKey, count: number, o: DayOptions = {}): DailyHealthData[] {
  return Array.from({ length: count }, (_, i) => makeDay(addDays(end, i - count), o));
}
