import { z } from 'zod';

/** Shape Claude must return for the daily briefing (structured outputs). */
export const briefingSchema = z.object({
  headline: z.string(),
  summary: z.string(),
  focus: z.enum(['recover', 'maintain', 'build', 'peak']),
  recommendations: z.array(z.string()),
  key_metric: z.enum([
    'hrv',
    'resting_heart_rate',
    'sleep',
    'strain',
    'sleep_debt',
    'body_battery',
    'training_load',
  ]),
});

export type BriefingOutput = z.infer<typeof briefingSchema>;
