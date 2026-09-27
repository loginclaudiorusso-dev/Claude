import type {
  DailyHealthData,
  DayKey,
  HeartRateSample,
  SleepSegment,
  SleepStage,
  Workout,
} from '@/types/health';
import { HOUR_MS, MINUTE_MS, addDays, round, startOfDay, toDayKey } from '@/utils/analytics';

/**
 * Deterministic, realistic demo history for the simulator, web and screenshots
 * (no HealthKit there). A seeded PRNG keeps values stable across reloads.
 */

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface PlannedWorkout {
  type: Workout['type'];
  name: string;
  minutes: number;
  hr: number;
  kcalPerMin: number;
}

const WEEK_PLAN: (PlannedWorkout | null)[] = [
  { type: 'strength', name: 'Krafttraining', minutes: 50, hr: 125, kcalPerMin: 6 },
  { type: 'running', name: 'Lauf – locker', minutes: 45, hr: 145, kcalPerMin: 11 },
  null,
  { type: 'hiit', name: 'HIIT', minutes: 30, hr: 162, kcalPerMin: 12 },
  { type: 'cycling', name: 'Radfahren', minutes: 75, hr: 138, kcalPerMin: 9 },
  { type: 'running', name: 'Lauf – lang', minutes: 80, hr: 150, kcalPerMin: 11 },
  null,
];

function buildSleep(bed: number, hours: number, rand: () => number): SleepSegment[] {
  const wake = bed + hours * HOUR_MS;
  const segments: SleepSegment[] = [{ start: bed, end: wake, stage: 'inBed' }];
  let t = bed + (8 + rand() * 12) * MINUTE_MS;
  segments.push({ start: bed, end: t, stage: 'awake' });
  let cycle = 0;
  while (t < wake) {
    // Deep sleep dominates early cycles, REM later ones.
    const early = Math.max(0, 1 - cycle / 4);
    const plan: [SleepStage, number][] = [
      ['core', 20 + rand() * 10],
      ['deep', 8 + early * 25 + rand() * 6],
      ['core', 15 + rand() * 10],
      ['rem', 10 + (1 - early) * 20 + rand() * 6],
      ['awake', rand() < 0.4 ? 2 + rand() * 4 : 0],
    ];
    for (const [stage, minutes] of plan) {
      if (minutes <= 0 || t >= wake) continue;
      const end = Math.min(wake, t + minutes * MINUTE_MS);
      segments.push({ start: t, end, stage });
      t = end;
    }
    cycle++;
  }
  return segments;
}

function buildHeartRate(
  wake: number,
  dayEnd: number,
  rhr: number,
  workouts: Workout[],
  rand: () => number,
): HeartRateSample[] {
  const samples: HeartRateSample[] = [];
  for (let t = wake; t < dayEnd; t += 5 * MINUTE_MS) {
    const hour = new Date(t).getHours();
    const activity = hour >= 8 && hour <= 20 ? 12 + rand() * 18 : 6 + rand() * 6;
    samples.push({ timestamp: t, bpm: Math.round(rhr + activity) });
  }
  for (const w of workouts) {
    for (let t = w.start; t < w.end; t += MINUTE_MS) {
      const progress = (t - w.start) / (w.end - w.start);
      const warmup = Math.min(1, progress * 6);
      samples.push({
        timestamp: t,
        bpm: Math.round(w.avgHeartRate! * (0.8 + 0.2 * warmup) + (rand() - 0.5) * 8),
      });
    }
  }
  return samples.sort((a, b) => a.timestamp - b.timestamp);
}

/** Generates `days` days of demo data ending today (today only up to `now`). */
export function generateDemoDays(
  days = 45,
  now: number = Date.now(),
  seed = 42,
): DailyHealthData[] {
  const rand = mulberry32(seed);
  const today = toDayKey(now);
  const result: DailyHealthData[] = [];
  let fatigue = 0;

  for (let i = days - 1; i >= 0; i--) {
    const date: DayKey = addDays(today, -i);
    const midnight = startOfDay(date);
    const weekday = (new Date(midnight).getDay() + 6) % 7;
    const plan = WEEK_PLAN[weekday] ?? null;

    // Harder days raise next-morning fatigue → lower HRV, higher RHR.
    const sleepHours = 6.4 + rand() * 1.8 - (weekday === 5 ? 0.6 : 0);
    const hrv = round(58 * (1 - fatigue * 0.18) * (0.9 + rand() * 0.2), 1);
    const rhr = round(52 + fatigue * 4 + rand() * 2.5, 0);

    const bed = midnight - (1 + rand()) * HOUR_MS;
    const wake = bed + sleepHours * HOUR_MS;
    const dayEnd = Math.min(midnight + 24 * HOUR_MS, now);

    const workouts: Workout[] = [];
    if (plan) {
      const start = midnight + (weekday >= 5 ? 9.5 : 18) * HOUR_MS;
      const minutes = Math.round(plan.minutes * (0.9 + rand() * 0.2));
      const end = start + minutes * MINUTE_MS;
      if (end <= dayEnd) {
        workouts.push({
          id: `demo-${date}`,
          type: plan.type,
          name: plan.name,
          start,
          end,
          activeEnergyKcal: Math.round(minutes * plan.kcalPerMin),
          avgHeartRate: Math.round(plan.hr + rand() * 6),
          distanceMeters:
            plan.type === 'running'
              ? Math.round(minutes * 170)
              : plan.type === 'cycling'
                ? minutes * 450
                : undefined,
        });
      }
    }
    fatigue = Math.min(1.5, fatigue * 0.55 + (plan ? plan.minutes * plan.hr : 0) / 9000);

    const heartRate = wake < dayEnd ? buildHeartRate(wake, dayEnd, rhr, workouts, rand) : [];
    const workoutKcal = workouts.reduce((acc, w) => acc + w.activeEnergyKcal, 0);
    const dayFraction = Math.min(1, (dayEnd - midnight) / (24 * HOUR_MS));

    result.push({
      date,
      source: 'demo',
      hrvSamples: [1.5, 3.5, 5].map((h) => ({
        timestamp: bed + h * HOUR_MS,
        sdnnMs: round(hrv * (0.92 + rand() * 0.16), 1),
      })),
      restingHeartRate: rhr,
      heartRateSamples: heartRate,
      sleep:
        wake <= now
          ? { start: bed, end: wake, segments: buildSleep(bed, sleepHours, rand) }
          : undefined,
      steps: Math.round((6500 + rand() * 6000) * dayFraction),
      activeEnergyKcal: Math.round((320 + rand() * 180) * dayFraction + workoutKcal),
      basalEnergyKcal: Math.round(1680 * dayFraction),
      vo2Max: round(47.5 + (days - i) * 0.02, 1),
      respiratoryRate: round(14 + rand() * 1.5, 1),
      workouts,
    });
  }
  return result;
}
