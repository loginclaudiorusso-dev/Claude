import type { DayKey, RecoveryZone, StrainLevel, Timestamp, TrendDirection } from './health';

/**
 * Compact, model-friendly JSON snapshot of one day that is sent to Claude.
 * Numbers are pre-rounded so the prompt stays small and deterministic.
 */
export interface CoachDailyPayload {
  date: DayKey;
  readiness: {
    score: number;
    zone: RecoveryZone;
    confidence: 'calibrating' | 'low' | 'high';
    hrvMs: number | null;
    hrvDeviationPct: number | null;
    restingHeartRate: number | null;
    restingHeartRateDeviationBpm: number | null;
  } | null;
  sleep: {
    totalHours: number;
    needHours: number;
    performancePct: number;
    efficiencyPct: number;
    deepPct: number | null;
    remPct: number | null;
    debtHours: number;
    score: number;
  } | null;
  strain: {
    yesterday: number | null;
    today: number;
    level: StrainLevel;
    targetRange: [number, number] | null;
    zoneMinutes: { z1: number; z2: number; z3: number; z4: number; z5: number };
  };
  bodyBattery: { current: number; startOfDay: number } | null;
  activity: {
    steps: number;
    activeEnergyKcal: number;
    workouts: {
      type: string;
      durationMin: number;
      activeEnergyKcal: number;
      avgHeartRate: number | null;
    }[];
    vo2Max: number | null;
  };
  trends7d: {
    hrv: TrendDirection;
    restingHeartRate: TrendDirection;
    sleep: TrendDirection;
    acuteChronicRatio: number | null;
  };
}

export type CoachFocus = 'recover' | 'maintain' | 'build' | 'peak';

/** Structured daily briefing returned by Claude (validated with zod). */
export interface CoachInsight {
  date: DayKey;
  headline: string;
  summary: string;
  focus: CoachFocus;
  recommendations: string[];
  /** Metric the coach considers most important today, e.g. "hrv". */
  keyMetric?: string;
  generatedAt: Timestamp;
}

/** UI-level chat message (the API conversation uses the SDK's MessageParam). */
export interface CoachChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  createdAt: Timestamp;
  status?: 'streaming' | 'done' | 'error';
}
