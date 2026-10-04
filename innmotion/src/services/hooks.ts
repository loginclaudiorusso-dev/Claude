// Lese-Hooks für die Screens. Für ein echtes Backend würden diese Hooks auf einen
// Query-Cache (z. B. TanStack Query + Supabase Realtime) umgestellt – die Screens bleiben gleich.

import { useEffect, useState } from 'react';
import { useDbStore, useSession } from './mock/store';
import type { Person, Site } from '../domain/types';

export const useDb = () => useDbStore((s) => s.db);

export function useMe(): Person | undefined {
  const db = useDb();
  const role = useSession((s) => s.role);
  const id = useSession((s) => s.personByRole[role]);
  return db.persons.find((p) => p.id === id);
}

export function useSite(siteId: string | undefined): Site | undefined {
  const db = useDb();
  return db.sites.find((s) => s.id === siteId);
}

/** Aktuelle Zeit, aktualisiert sich im angegebenen Intervall. */
export function useNow(intervalMs = 30_000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    const mq = matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduced(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return reduced;
}
