import type {
  DailyHealthData,
  DayKey,
  HeartRateSample,
  SleepSegment,
  SleepSession,
  Workout,
} from '@/types/health';
import {
  HOUR_MS,
  MINUTE_MS,
  addDays,
  endOfDay,
  mean,
  median,
  round,
  startOfDay,
  sum,
  toDayKey,
} from '@/utils/analytics';

import type { RawHealthRecords, ValueSample } from './raw';

/** Sleep segments further apart than this start a new session. */
const SESSION_GAP_MS = 2 * HOUR_MS;
/** Sessions shorter than this are naps, never the main night. */
const MIN_MAIN_SLEEP_MS = 3 * HOUR_MS;
/** HR series sparser than this are aggregates (e.g. hourly averages) – unusable for TRIMP. */
const MAX_HR_SPACING_MS = 10 * MINUTE_MS;

function groupByDay<T extends { timestamp: number }>(items: readonly T[]): Map<DayKey, T[]> {
  const map = new Map<DayKey, T[]>();
  for (const item of items) {
    const key = toDayKey(item.timestamp);
    const list = map.get(key);
    if (list) list.push(item);
    else map.set(key, [item]);
  }
  return map;
}

/** Removes exact duplicates (same timestamp) that appear when sources overlap. */
function dedupeByTimestamp<T extends { timestamp: number }>(items: readonly T[]): T[] {
  const seen = new Set<number>();
  return [...items]
    .sort((a, b) => a.timestamp - b.timestamp)
    .filter((s) => (seen.has(s.timestamp) ? false : (seen.add(s.timestamp), true)));
}

/** Clusters sleep segments into sessions separated by gaps > 2 h. */
export function clusterSleepSessions(segments: readonly SleepSegment[]): SleepSession[] {
  const sorted = [...segments].filter((s) => s.end > s.start).sort((a, b) => a.start - b.start);
  const sessions: SleepSession[] = [];
  for (const seg of sorted) {
    const current = sessions.at(-1);
    if (current && seg.start - current.end <= SESSION_GAP_MS) {
      current.segments.push(seg);
      current.end = Math.max(current.end, seg.end);
    } else {
      sessions.push({ start: seg.start, end: seg.end, segments: [seg] });
    }
  }
  return sessions;
}

/** The longest session ending on each day (≥ 3 h) is that day's main sleep. */
function mainSleepByDay(segments: readonly SleepSegment[]): Map<DayKey, SleepSession> {
  const map = new Map<DayKey, SleepSession>();
  for (const session of clusterSleepSessions(segments)) {
    if (session.end - session.start < MIN_MAIN_SLEEP_MS) continue;
    const key = toDayKey(session.end);
    const existing = map.get(key);
    if (!existing || session.end - session.start > existing.end - existing.start)
      map.set(key, session);
  }
  return map;
}

function isDenseHeartRate(samples: readonly HeartRateSample[]): boolean {
  if (samples.length < 2) return false;
  const gaps = samples.slice(1).map((s, i) => s.timestamp - samples[i]!.timestamp);
  return (median(gaps) ?? Infinity) <= MAX_HR_SPACING_MS;
}

/** Fills missing workout avg/max HR from the heart-rate series. */
function enrichWorkout(w: Workout, hr: readonly HeartRateSample[]): Workout {
  if (w.avgHeartRate && w.maxHeartRate) return w;
  const inside = hr.filter((s) => s.timestamp >= w.start && s.timestamp <= w.end).map((s) => s.bpm);
  if (inside.length === 0) return w;
  return {
    ...w,
    avgHeartRate: w.avgHeartRate ?? round(mean(inside)!),
    maxHeartRate: w.maxHeartRate ?? Math.max(...inside),
  };
}

const sumValues = (s?: readonly ValueSample[]) => (s ? sum(s.map((v) => v.value)) : 0);
const meanValue = (s?: readonly ValueSample[]) => {
  const m = s && s.length > 0 ? mean(s.map((v) => v.value)) : null;
  return m === null ? undefined : round(m, 1);
};

/**
 * Normalises raw records into one `DailyHealthData` per calendar day, sorted
 * ascending. Only days with at least one data point are returned.
 */
export function buildDailyHealthData(raw: RawHealthRecords): DailyHealthData[] {
  const heartRate = dedupeByTimestamp(raw.heartRate.filter((s) => s.bpm > 25 && s.bpm < 250));
  const hrv = dedupeByTimestamp(raw.hrv.filter((s) => s.sdnnMs > 0 && s.sdnnMs < 400));
  const workouts = [
    ...new Map(raw.workouts.map((w) => [w.id, enrichWorkout(w, heartRate)])).values(),
  ];

  const hrByDay = groupByDay(heartRate);
  const hrvByDay = groupByDay(hrv);
  const rhrByDay = groupByDay(raw.restingHeartRate);
  const stepsByDay = groupByDay(raw.steps);
  const activeByDay = groupByDay(raw.activeEnergyKcal);
  const basalByDay = groupByDay(raw.basalEnergyKcal);
  const vo2ByDay = groupByDay(raw.vo2Max);
  const respByDay = groupByDay(raw.respiratoryRate);
  const workoutsByDay = groupByDay(workouts.map((w) => ({ ...w, timestamp: w.start })));
  const sleepByDay = mainSleepByDay(raw.sleepSegments);

  const days = new Set<DayKey>([
    ...hrByDay.keys(),
    ...hrvByDay.keys(),
    ...rhrByDay.keys(),
    ...stepsByDay.keys(),
    ...activeByDay.keys(),
    ...workoutsByDay.keys(),
    ...sleepByDay.keys(),
  ]);

  return [...days].sort().map((date): DailyHealthData => {
    const dayHr = hrByDay.get(date) ?? [];
    const dayWorkouts = (workoutsByDay.get(date) ?? []).map(({ timestamp: _t, ...w }) => w);
    const workoutKcal = sum(dayWorkouts.map((w) => w.activeEnergyKcal));
    return {
      date,
      source: raw.source,
      hrvSamples: hrvByDay.get(date) ?? [],
      restingHeartRate: meanValue(rhrByDay.get(date)),
      heartRateSamples: isDenseHeartRate(dayHr) ? dayHr : [],
      sleep: sleepByDay.get(date),
      steps: Math.round(sumValues(stepsByDay.get(date))),
      // Some exports omit active energy outside workouts – never report less than the workouts burned.
      activeEnergyKcal: Math.round(Math.max(sumValues(activeByDay.get(date)), workoutKcal)),
      basalEnergyKcal: basalByDay.has(date)
        ? Math.round(sumValues(basalByDay.get(date)))
        : undefined,
      vo2Max: meanValue(vo2ByDay.get(date)),
      respiratoryRate: meanValue(respByDay.get(date)),
      workouts: dayWorkouts,
    };
  });
}

/**
 * Merges freshly loaded days into an existing collection; newer data for the
 * same day replaces the old entry. Result is sorted ascending.
 */
export function mergeDays(
  existing: readonly DailyHealthData[],
  incoming: readonly DailyHealthData[],
): DailyHealthData[] {
  const map = new Map(existing.map((d) => [d.date, d]));
  for (const d of incoming) map.set(d.date, d);
  return [...map.values()].sort((a, b) => a.date.localeCompare(b.date));
}

/** Inclusive date range as timestamps: from local midnight of `from` to end of `to`. */
export function dayRangeBounds(from: DayKey, to: DayKey): { start: number; end: number } {
  return { start: startOfDay(from), end: endOfDay(to) };
}

/** `[today − (days − 1), today]` as day keys. */
export function lookbackRange(
  days: number,
  today: DayKey = toDayKey(Date.now()),
): { from: DayKey; to: DayKey } {
  return { from: addDays(today, -(days - 1)), to: today };
}
