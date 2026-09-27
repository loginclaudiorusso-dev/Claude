import {
  acuteChronicRatio,
  analyzeSleep,
  buildTrend,
  buildTrendReport,
  calculateSleepNeed,
  computeBaselines,
  computeReadiness,
  computeStrain,
  estimateMaxHeartRate,
  heartRateZone,
  linearSlope,
  nightlyHrv,
  recommendedStrainTarget,
  startLevelFromReadiness,
  summarizeDay,
  summarizeHistory,
  trimpToStrain,
  updateSleepDebt,
  zScoreToScore,
} from '../analytics';
import { addDays } from '../time';

import { makeDay, makeHistory } from '@/test/fixtures';

const TODAY = '2026-09-20';
const hrOpts = { restingHeartRate: 55, maxHeartRate: 190 };

describe('stats', () => {
  it('computes slopes and ignores nulls', () => {
    expect(linearSlope([1, 2, 3, 4])).toBeCloseTo(1);
    expect(linearSlope([null, 2, null, 4])).toBeCloseTo(1);
    expect(linearSlope([5])).toBeNull();
  });
});

describe('heart rate', () => {
  it('estimates max HR with Tanaka and prefers measured values', () => {
    expect(estimateMaxHeartRate({ birthYear: 1986 }, new Date(2026, 5, 1))).toBe(180);
    expect(estimateMaxHeartRate({ birthYear: 1986, maxHeartRate: 195 })).toBe(195);
  });

  it('maps heart-rate reserve to zones', () => {
    expect(heartRateZone(0.4)).toBeNull();
    expect(heartRateZone(0.55)).toBe(1);
    expect(heartRateZone(0.75)).toBe(3);
    expect(heartRateZone(0.95)).toBe(5);
  });
});

describe('readiness', () => {
  const history = makeHistory(TODAY, 7, { hrv: 50, rhr: 55 });
  const baselines = computeBaselines(history);

  it('uses nightly HRV samples only', () => {
    expect(nightlyHrv(makeDay(TODAY, { hrv: 60 }))).toBe(60);
  });

  it('builds a 7-day baseline on ln(HRV)', () => {
    expect(baselines.lnHrv?.n).toBe(7);
    expect(baselines.lnHrv?.mean).toBeCloseTo(Math.log(50));
    expect(baselines.restingHeartRate?.mean).toBe(55);
  });

  it('maps z = 0 to ~62 % and is monotonic', () => {
    expect(zScoreToScore(0)).toBeCloseTo(62.2, 0);
    expect(zScoreToScore(1)).toBeGreaterThan(zScoreToScore(0));
    expect(zScoreToScore(-2)).toBeLessThan(15);
  });

  it('drops when HRV is 12 % below baseline and RHR is elevated', () => {
    const normal = computeReadiness(
      { hrvMs: 50, restingHeartRate: 55, sleepScore: 85 },
      baselines,
    )!;
    const stressed = computeReadiness(
      { hrvMs: 44, restingHeartRate: 60, sleepScore: 85 },
      baselines,
    )!;
    expect(stressed.hrvDeviationPct).toBeCloseTo(-12, 1);
    expect(stressed.restingHeartRateDeviationBpm).toBe(5);
    expect(stressed.score).toBeLessThan(normal.score - 20);
    expect(stressed.zone).not.toBe('green');
    expect(stressed.score).toBeLessThan(45);
    expect(normal.confidence).toBe('high');
  });

  it('falls back to sleep only while calibrating', () => {
    const r = computeReadiness(
      { hrvMs: 50, restingHeartRate: 55, sleepScore: 80 },
      computeBaselines([]),
    )!;
    expect(r.score).toBe(80);
    expect(r.confidence).toBe('calibrating');
    expect(r.components.hrv).toBeUndefined();
  });

  it('returns undefined without any input', () => {
    expect(computeReadiness({}, baselines)).toBeUndefined();
  });
});

describe('strain', () => {
  it('saturates towards 21', () => {
    expect(trimpToStrain(0)).toBe(0);
    expect(trimpToStrain(100)).toBeCloseTo(12.5, 1);
    expect(trimpToStrain(10_000)).toBe(21);
  });

  it('integrates heart-rate samples and zone minutes', () => {
    const rest = computeStrain(makeDay(TODAY, { withHeartRate: true }), hrOpts);
    const run = computeStrain(makeDay(TODAY, { withHeartRate: true, workoutHr: 160 }), hrOpts);
    expect(rest.method).toBe('heartRate');
    expect(rest.score).toBe(0);
    expect(run.zoneMinutes[3]).toBe(60); // 160 bpm ≈ 78 % HRR
    expect(run.workoutTrimp).toBeCloseTo(run.trimp);
    expect(run.score).toBeGreaterThan(10);
    expect(run.score).toBeLessThan(18);
  });

  it('falls back to workout averages, then energy', () => {
    const workout = computeStrain(makeDay(TODAY, { workoutHr: 160 }), hrOpts);
    expect(workout.method).toBe('workoutEstimate');
    const energy = computeStrain(makeDay(TODAY, { activeEnergyKcal: 600 }), hrOpts);
    expect(energy.method).toBe('energyEstimate');
    expect(energy.trimp).toBe(90);
  });

  it('recommends a range that grows with readiness', () => {
    expect(recommendedStrainTarget(0)).toEqual({ min: 2.5, max: 5.5 });
    expect(recommendedStrainTarget(100)).toEqual({ min: 16.5, max: 19.5 });
  });
});

describe('sleep', () => {
  it('splits stages and ignores the inBed envelope', () => {
    const a = analyzeSleep(makeDay(TODAY, { sleepHours: 8 }).sleep!);
    expect(a.timeInBedMinutes).toBe(480);
    expect(a.stages.awake).toBe(24);
    expect(a.totalSleepMinutes).toBe(456);
    expect(a.stageShare?.deep).toBeCloseTo(0.179, 2);
    expect(a.efficiency).toBeCloseTo(0.95);
    expect(a.score).toBeGreaterThan(90);
  });

  it('does not double-count overlapping sources', () => {
    const session = makeDay(TODAY).sleep!;
    const doubled = { ...session, segments: [...session.segments, ...session.segments] };
    expect(analyzeSleep(doubled).totalSleepMinutes).toBe(analyzeSleep(session).totalSleepMinutes);
  });

  it('handles unstaged sleep', () => {
    const a = analyzeSleep(makeDay(TODAY, { staged: false }).sleep!);
    expect(a.stageShare).toBeUndefined();
    expect(a.stages.unspecified).toBe(480);
  });

  it('raises need after strain and repays debt', () => {
    expect(calculateSleepNeed(480, 16, 0)).toBe(516);
    expect(calculateSleepNeed(480, 0, 400)).toBe(540);
    expect(updateSleepDebt(0, 360, 480)).toBe(120);
    expect(updateSleepDebt(100, 600, 480)).toBe(0);
  });

  it('penalises short nights', () => {
    const short = analyzeSleep(makeDay(TODAY, { sleepHours: 5 }).sleep!);
    expect(short.performancePct).toBeLessThan(60);
    expect(short.debtMinutes).toBeGreaterThan(180);
  });
});

describe('body battery', () => {
  it('starts from readiness and drains more on active days', () => {
    expect(startLevelFromReadiness(100)).toBe(100);
    const calm = summarizeDay(makeDay(TODAY, { withHeartRate: true }), makeHistory(TODAY, 7));
    const active = summarizeDay(
      makeDay(TODAY, { withHeartRate: true, workoutHr: 165 }),
      makeHistory(TODAY, 7),
    );
    expect(calm.bodyBattery!.startLevel).toBe(active.bodyBattery!.startLevel);
    expect(active.bodyBattery!.currentLevel).toBeLessThan(calm.bodyBattery!.currentLevel - 20);
    expect(calm.bodyBattery!.points.length).toBeGreaterThan(50);
  });

  it('stops at `now` for today', () => {
    const day = makeDay(TODAY, { withHeartRate: true });
    const noon = day.sleep!.end + 5 * 3_600_000;
    const s = summarizeDay(day, [], {}, { now: noon });
    expect(s.bodyBattery!.points.at(-1)!.timestamp).toBe(noon);
  });
});

describe('history & trends', () => {
  const days = [
    ...makeHistory(addDays(TODAY, -6), 24, { hrv: 50, withHeartRate: true, workoutHr: 150 }),
    ...Array.from({ length: 7 }, (_, i) =>
      makeDay(addDays(TODAY, i - 6), {
        hrv: 50 + i * 3,
        rhr: 55 - i * 0.5,
        withHeartRate: true,
        workoutHr: 170,
      }),
    ),
  ];
  const summaries = summarizeHistory(days, { sex: 'male', birthYear: 1990 });

  it('chains days chronologically', () => {
    expect(summaries).toHaveLength(31);
    expect(summaries.at(-1)!.date).toBe(TODAY);
    expect(summaries[0]!.readiness?.confidence).toBe('calibrating');
    expect(summaries.at(-1)!.readiness?.confidence).toBe('high');
    // Previous day's battery feeds the overnight segment.
    expect(summaries.at(-1)!.bodyBattery!.points[0]!.level).toBe(
      summaries.at(-2)!.bodyBattery!.currentLevel,
    );
  });

  it('detects rising HRV and falling RHR', () => {
    const report = buildTrendReport(summaries, 7)!;
    expect(report.hrv.direction).toBe('up');
    expect(report.restingHeartRate.direction).toBe('down');
    expect(report.hrv.points).toHaveLength(7);
    expect(buildTrendReport(summaries, 30)!.strain.points).toHaveLength(30);
  });

  it('computes an elevated acute:chronic ratio after a harder week', () => {
    const acwr = acuteChronicRatio(summaries, TODAY)!;
    expect(acwr).toBeGreaterThan(1);
  });

  it('marks tiny changes as flat and fills gaps with null', () => {
    const t = buildTrend([
      { date: 'a', value: 100 },
      { date: 'b', value: null },
      { date: 'c', value: 101 },
    ]);
    expect(t.direction).toBe('flat');
    expect(t.average).toBe(100.5);
  });
});
