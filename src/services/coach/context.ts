import type { DailyHealthData, DailySummary } from '@/types/health';

/** Everything the coach may read: raw days (for workouts) and computed summaries. */
export interface CoachContext {
  days: readonly DailyHealthData[];
  summaries: readonly DailySummary[];
}
