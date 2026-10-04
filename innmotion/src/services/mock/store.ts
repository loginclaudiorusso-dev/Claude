// Lokaler Datenspeicher des Prototyps (Zustand + localStorage).
// Wird ausschließlich über `mockApi` verändert; Screens lesen über die Hooks in `services/hooks.ts`.

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { generateSeed, DB_VERSION, DEMO_IDS } from '../../seed/generate';
import type { DB, Role } from '../../domain/types';

interface DbState {
  db: DB;
  setDb: (fn: (db: DB) => DB) => void;
  reset: () => void;
}

export const useDbStore = create<DbState>()(
  persist(
    (set) => ({
      db: generateSeed(),
      setDb: (fn) => set((s) => ({ db: fn(s.db) })),
      reset: () => set({ db: generateSeed() }),
    }),
    {
      name: 'innmotion-db',
      version: DB_VERSION,
      storage: createJSONStorage(() => localStorage),
      // Neue Datenstruktur → Demo-Daten neu erzeugen.
      migrate: () => ({ db: generateSeed() }) as unknown as DbState,
    },
  ),
);

// Frisch erzeugte Demo-Daten sofort speichern, damit sie nach dem Neuladen gleich bleiben.
try {
  if (!localStorage.getItem('innmotion-db')) useDbStore.getState().setDb((db) => ({ ...db }));
} catch {
  /* Speicher nicht verfügbar (z. B. privater Modus) – Demo läuft dann nur im Arbeitsspeicher. */
}

export interface Session {
  role: Role;
  /** Aktive Demo-Person je Rolle. */
  personByRole: Record<Role, string>;
  setRole: (role: Role) => void;
  setPerson: (role: Role, personId: string) => void;
}

export const useSession = create<Session>()(
  persist(
    (set) => ({
      role: 'participant',
      personByRole: { participant: DEMO_IDS.participant, staff: DEMO_IDS.staff, lead: DEMO_IDS.lead },
      setRole: (role) => set({ role }),
      setPerson: (role, personId) => set((s) => ({ personByRole: { ...s.personByRole, [role]: personId } })),
    }),
    { name: 'innmotion-session', version: 1 },
  ),
);

export type ThemePref = 'system' | 'light' | 'dark';

interface Prefs {
  theme: ThemePref;
  largeText: boolean;
  setTheme: (t: ThemePref) => void;
  setLargeText: (v: boolean) => void;
}

/** Geräte-Einstellungen (Darstellung). */
export const usePrefs = create<Prefs>()(
  persist(
    (set) => ({
      theme: 'system',
      largeText: false,
      setTheme: (theme) => set({ theme }),
      setLargeText: (largeText) => set({ largeText }),
    }),
    { name: 'innmotion-prefs', version: 1 },
  ),
);
