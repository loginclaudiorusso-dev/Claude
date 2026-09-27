import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { HealthDataMode } from '@/services/health';
import type { UserProfile } from '@/types/health';

import { fileStorage } from './fileStorage';

interface SettingsState {
  profile: UserProfile;
  /** null until the user (or auto-detection) picked a data source. */
  dataMode: HealthDataMode | null;
  healthKitConnected: boolean;
  setProfile: (patch: Partial<UserProfile>) => void;
  setDataMode: (mode: HealthDataMode) => void;
  setHealthKitConnected: (connected: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      profile: { sleepNeedMinutes: 480 },
      dataMode: null,
      healthKitConnected: false,
      setProfile: (patch) => set((s) => ({ profile: { ...s.profile, ...patch } })),
      setDataMode: (dataMode) => set({ dataMode }),
      setHealthKitConnected: (healthKitConnected) => set({ healthKitConnected }),
    }),
    {
      name: 'pulse-settings.v1',
      storage: createJSONStorage(() => fileStorage),
      partialize: ({ profile, dataMode, healthKitConnected }) => ({
        profile,
        dataMode,
        healthKitConnected,
      }),
    },
  ),
);
