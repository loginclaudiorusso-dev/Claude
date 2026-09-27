import { HOUR_MS, MINUTE_MS, startOfDay } from '@/utils/analytics';

import { buildDailyHealthData, clusterSleepSessions, mergeDays } from '../buildDays';
import { classifyWorkout, emptyRecords } from '../raw';

const DAY = '2026-09-20';
const midnight = startOfDay(DAY);

describe('buildDailyHealthData', () => {
  it('assigns the night to the day it ends and ignores naps', () => {
    const raw = emptyRecords('healthkit');
    raw.sleepSegments = [
      { start: midnight - 1 * HOUR_MS, end: midnight + 3 * HOUR_MS, stage: 'core' },
      { start: midnight + 3.5 * HOUR_MS, end: midnight + 7 * HOUR_MS, stage: 'deep' }, // 30 min gap → same session
      { start: midnight + 14 * HOUR_MS, end: midnight + 14.5 * HOUR_MS, stage: 'core' }, // nap
    ];
    const [day] = buildDailyHealthData(raw);
    expect(day!.date).toBe(DAY);
    expect(day!.sleep!.start).toBe(midnight - HOUR_MS);
    expect(day!.sleep!.end).toBe(midnight + 7 * HOUR_MS);
    expect(clusterSleepSessions(raw.sleepSegments)).toHaveLength(2);
  });

  it('sums additive metrics, averages vitals and dedupes samples', () => {
    const raw = emptyRecords('import');
    raw.steps = [
      { timestamp: midnight + 9 * HOUR_MS, value: 3000 },
      { timestamp: midnight + 15 * HOUR_MS, value: 4500 },
    ];
    raw.activeEnergyKcal = [{ timestamp: midnight + 10 * HOUR_MS, value: 250 }];
    raw.restingHeartRate = [
      { timestamp: midnight + 8 * HOUR_MS, value: 52 },
      { timestamp: midnight + 20 * HOUR_MS, value: 54 },
    ];
    raw.hrv = [
      { timestamp: midnight + 2 * HOUR_MS, sdnnMs: 50 },
      { timestamp: midnight + 2 * HOUR_MS, sdnnMs: 50 },
    ];
    const [day] = buildDailyHealthData(raw);
    expect(day!.steps).toBe(7500);
    expect(day!.restingHeartRate).toBe(53);
    expect(day!.hrvSamples).toHaveLength(1);
    expect(day!.source).toBe('import');
  });

  it('keeps dense HR, drops hourly aggregates and enriches workouts', () => {
    const dense = emptyRecords('healthkit');
    const start = midnight + 18 * HOUR_MS;
    for (let t = start; t < start + 30 * MINUTE_MS; t += MINUTE_MS)
      dense.heartRate.push({ timestamp: t, bpm: 150 });
    dense.workouts = [
      { id: 'w', type: 'running', start, end: start + 30 * MINUTE_MS, activeEnergyKcal: 300 },
    ];
    const [d1] = buildDailyHealthData(dense);
    expect(d1!.heartRateSamples).toHaveLength(30);
    expect(d1!.workouts[0]!.avgHeartRate).toBe(150);
    expect(d1!.activeEnergyKcal).toBe(300);

    const hourly = emptyRecords('import');
    for (let h = 0; h < 24; h++)
      hourly.heartRate.push({ timestamp: midnight + h * HOUR_MS, bpm: 70 });
    expect(buildDailyHealthData(hourly)[0]!.heartRateSamples).toHaveLength(0);
  });

  it('merges newer data over older days', () => {
    const a = buildDailyHealthData({
      ...emptyRecords('import'),
      steps: [{ timestamp: midnight + HOUR_MS * 10, value: 1 }],
    });
    const b = buildDailyHealthData({
      ...emptyRecords('import'),
      steps: [{ timestamp: midnight + HOUR_MS * 10, value: 2 }],
    });
    expect(mergeDays(a, b)).toEqual(b);
  });
});

describe('classifyWorkout', () => {
  it.each([
    ['Outdoor Run', 'running'],
    ['TraditionalStrengthTraining', 'strength'],
    ['High Intensity Interval Training', 'hiit'],
    ['Indoor Cycling', 'cycling'],
    ['Hiking', 'hiking'],
    ['Tennis', 'other'],
  ])('%s → %s', (name, type) => expect(classifyWorkout(name)).toBe(type));
});
