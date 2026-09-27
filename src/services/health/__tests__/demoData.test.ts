import { buildTrendReport, summarizeHistory } from '@/utils/analytics';

import { generateDemoDays } from '../demoData';

describe('demo data', () => {
  const now = new Date(2026, 8, 20, 15, 30).getTime();
  const days = generateDemoDays(45, now);
  const summaries = summarizeHistory(days, { birthYear: 1990, sex: 'male' }, now);

  it('is deterministic', () => {
    expect(generateDemoDays(45, now)).toEqual(days);
  });

  it('produces plausible scores for every day', () => {
    expect(days).toHaveLength(45);
    for (const s of summaries.slice(7)) {
      expect(s.readiness!.score).toBeGreaterThanOrEqual(0);
      expect(s.readiness!.score).toBeLessThanOrEqual(100);
      expect(s.strain.score).toBeLessThanOrEqual(21);
      expect(s.sleep!.totalSleepMinutes).toBeGreaterThan(300);
      expect(s.bodyBattery!.currentLevel).toBeGreaterThanOrEqual(0);
    }
    const strains = summaries.map((s) => s.strain.score);
    expect(Math.max(...strains)).toBeGreaterThan(12);
    expect(Math.min(...strains)).toBeLessThan(8);
    const zones = new Set(summaries.slice(7).map((s) => s.readiness!.zone));
    expect(zones.size).toBeGreaterThan(1);
  });

  it('stops today at `now` and supports 30-day trends', () => {
    const today = summaries.at(-1)!;
    expect(today.bodyBattery!.points.at(-1)!.timestamp).toBeLessThanOrEqual(now);
    expect(buildTrendReport(summaries, 30)!.acuteChronicRatio).not.toBeNull();
  });
});
