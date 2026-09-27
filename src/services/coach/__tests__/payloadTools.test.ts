import { generateDemoDays } from '@/services/health/demoData';
import { summarizeHistory } from '@/utils/analytics';

import type { CoachContext } from '../context';
import { buildCoachPayload } from '../payload';
import { COACH_TOOLS, executeCoachTool } from '../tools';

const now = new Date(2026, 8, 20, 15, 0).getTime();
const days = generateDemoDays(45, now);
const ctx: CoachContext = { days, summaries: summarizeHistory(days, { birthYear: 1990 }, now) };

describe('coach payload', () => {
  const payload = buildCoachPayload(ctx)!;

  it('describes the latest day compactly', () => {
    expect(payload.date).toBe('2026-09-20');
    expect(payload.readiness?.zone).toMatch(/green|yellow|red/);
    expect(payload.sleep?.totalHours).toBeGreaterThan(5);
    expect(payload.strain.yesterday).not.toBeNull();
    expect(payload.trends7d.acuteChronicRatio).not.toBeNull();
    expect(JSON.stringify(payload).length).toBeLessThan(2000);
  });

  it('is deterministic and null for unknown dates', () => {
    expect(buildCoachPayload(ctx)).toEqual(payload);
    expect(buildCoachPayload(ctx, '2020-01-01')).toBeNull();
  });
});

describe('coach tools', () => {
  const run = (name: string, input: unknown) => {
    const r = executeCoachTool(name, input, ctx);
    return { ...r, data: JSON.parse(r.content) };
  };

  it('declares strict schemas for every tool', () => {
    for (const tool of COACH_TOOLS) {
      expect(tool.strict).toBe(true);
      expect(tool.input_schema.additionalProperties).toBe(false);
    }
  });

  it('returns metric series with trend info', () => {
    const { data, isError } = run('get_metric_series', { metric: 'hrv', days: 14 });
    expect(isError).toBe(false);
    expect(data.points).toHaveLength(14);
    expect(['up', 'down', 'flat']).toContain(data.direction);
  });

  it('lists workouts with next-night sleep', () => {
    const { data } = run('list_workouts', { days: 14 });
    expect(data.length).toBeGreaterThan(5);
    expect(data[0]).toHaveProperty('nextNightSleepScore');
  });

  it('compares the day after training vs rest', () => {
    const { data } = run('compare_after_training', { metric: 'readiness', days: 30 });
    expect(data.afterTraining.days + data.afterRest.days).toBeGreaterThan(20);
    expect(typeof data.differencePct).toBe('number');
  });

  it('returns a day summary or an error for missing days', () => {
    expect(run('get_day_summary', { date: '2026-09-15' }).data.date).toBe('2026-09-15');
    expect(run('get_day_summary', { date: '2019-01-01' }).isError).toBe(true);
  });

  it('rejects invalid input and unknown tools', () => {
    expect(run('get_metric_series', { metric: 'mood', days: 7 }).isError).toBe(true);
    expect(run('get_metric_series', { metric: 'hrv', days: 500 }).isError).toBe(true);
    expect(run('delete_everything', {}).isError).toBe(true);
  });
});
