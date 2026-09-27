import { toDayKey } from '@/utils/analytics';
import { analyzeSleep } from '@/utils/sleep';

import { buildDailyHealthData } from '../buildDays';
import { UnsupportedImportError, parseHealthExport } from '../importers';
import { parseDate, parseNumber } from '../importers/parseUtils';

describe('parse utils', () => {
  it('parses Health Auto Export dates as wall-clock time', () => {
    expect(parseDate('2026-09-20 07:04:00 +0200')).toBe(new Date(2026, 8, 20, 7, 4).getTime());
    expect(toDayKey(parseDate('2026-09-20 00:00:00 +1400')!)).toBe('2026-09-20');
    expect(parseDate('2026-09-20T07:04:00Z')).toBe(Date.parse('2026-09-20T07:04:00Z'));
    expect(toDayKey(parseDate('2026-09-20')!)).toBe('2026-09-20');
    expect(parseDate('garbage')).toBeUndefined();
  });

  it('parses numbers with decimal commas and qty objects', () => {
    expect(parseNumber('1,5')).toBe(1.5);
    expect(parseNumber('1,234.5')).toBe(1234.5);
    expect(parseNumber({ qty: 42, units: 'kcal' })).toBe(42);
    expect(parseNumber('')).toBeUndefined();
  });
});

const haeJson = {
  data: {
    metrics: [
      {
        name: 'heart_rate_variability',
        units: 'ms',
        data: [{ date: '2026-09-20 03:00:00 +0200', qty: 48.5 }],
      },
      {
        name: 'resting_heart_rate',
        units: 'count/min',
        data: [{ date: '2026-09-20 00:00:00 +0200', qty: 53 }],
      },
      {
        name: 'step_count',
        units: 'count',
        data: [{ date: '2026-09-20 00:00:00 +0200', qty: 9123 }],
      },
      {
        name: 'active_energy',
        units: 'kJ',
        data: [{ date: '2026-09-20 00:00:00 +0200', qty: 2092 }],
      },
      {
        name: 'vo2_max',
        units: 'ml/(kg·min)',
        data: [{ date: '2026-09-20 00:00:00 +0200', qty: 48.1 }],
      },
      {
        name: 'sleep_analysis',
        units: 'hr',
        data: [
          {
            date: '2026-09-20 00:00:00 +0200',
            asleep: 7.1,
            core: 3.9,
            deep: 1.2,
            rem: 1.6,
            awake: 0.3,
            inBedStart: '2026-09-19 23:05:00 +0200',
            sleepEnd: '2026-09-20 06:40:00 +0200',
          },
        ],
      },
      { name: 'unknown_metric', data: [{ date: '2026-09-20', qty: 1 }] },
    ],
    workouts: [
      {
        id: 'abc',
        name: 'Outdoor Run',
        start: '2026-09-20 18:00:00 +0200',
        end: '2026-09-20 18:45:00 +0200',
        activeEnergyBurned: { qty: 480, units: 'kcal' },
        avgHeartRate: { qty: 152, units: 'bpm' },
        distance: { qty: 8.2, units: 'km' },
      },
    ],
  },
};

describe('Health Auto Export JSON', () => {
  const days = buildDailyHealthData(parseHealthExport(JSON.stringify(haeJson), 'export.json'));
  const day = days.find((d) => d.date === '2026-09-20')!;

  it('maps metrics, converts kJ and keeps workouts', () => {
    expect(day.hrvSamples[0]!.sdnnMs).toBe(48.5);
    expect(day.restingHeartRate).toBe(53);
    expect(day.steps).toBe(9123);
    expect(day.activeEnergyKcal).toBe(500);
    expect(day.vo2Max).toBe(48.1);
    expect(day.workouts[0]).toMatchObject({
      type: 'running',
      avgHeartRate: 152,
      distanceMeters: 8200,
    });
  });

  it('synthesises staged sleep from nightly totals', () => {
    const sleep = analyzeSleep(day.sleep!);
    expect(sleep.totalSleepMinutes).toBe(Math.round(7.1 * 60 - 0)); // deep+core+rem = 6.7 h + 0.4 h unstaged
    expect(sleep.stages.deep).toBe(72);
    expect(sleep.stages.rem).toBe(96);
    expect(sleep.timeInBedMinutes).toBe(455);
  });

  it('rejects unknown JSON', () => {
    expect(() => parseHealthExport('{"foo": 1}', 'x.json')).toThrow(UnsupportedImportError);
    expect(() => parseHealthExport('{broken', 'x.json')).toThrow(UnsupportedImportError);
  });
});

describe('CSV', () => {
  const csv = [
    'Date/Time;Heart Rate Variability (ms);Resting Heart Rate (count/min);Step Count (count);Active Energy (kcal);Sleep Analysis [Deep] (hr);Sleep Analysis [Core] (hr);Sleep Analysis [REM] (hr);Sleep Analysis [Awake] (hr)',
    '2026-09-19;52,3;54;10234;512;1,1;4,0;1,5;0,4',
    '2026-09-20;47,0;56;8000;430;0,9;3,5;1,2;0,5',
  ].join('\n');
  const days = buildDailyHealthData(parseHealthExport(csv, 'export.csv'));

  it('matches columns by name with semicolon delimiter and decimal commas', () => {
    expect(days.map((d) => d.date)).toEqual(['2026-09-19', '2026-09-20']);
    expect(days[0]!.hrvSamples[0]!.sdnnMs).toBe(52.3);
    expect(days[1]!.restingHeartRate).toBe(56);
    expect(days[0]!.activeEnergyKcal).toBe(512);
  });

  it('builds a sleep session ending 07:00 from totals', () => {
    const sleep = analyzeSleep(days[1]!.sleep!);
    expect(sleep.totalSleepMinutes).toBe(336);
    expect(sleep.stages.awake).toBe(30);
    expect(new Date(days[1]!.sleep!.end).getHours()).toBe(7);
  });

  it('rejects unrelated text', () => {
    expect(() => parseHealthExport('hello world', 'notes.txt')).toThrow(UnsupportedImportError);
  });
});
