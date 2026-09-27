import { useMemo } from 'react';

import type { CoachContext } from '@/services/claudeCoach';
import { useHealthStore } from '@/store/healthStore';

/** Stable coach context (raw days + summaries) from the health store. */
export function useCoachContext(): CoachContext {
  const days = useHealthStore((s) => s.days);
  const summaries = useHealthStore((s) => s.summaries);
  return useMemo(() => ({ days, summaries }), [days, summaries]);
}
