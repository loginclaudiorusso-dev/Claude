import { create } from 'zustand';

import {
  type HealthDataMode,
  deleteLocalHealthData,
  detectDefaultMode,
  importHealthFile,
  loadHealthDays,
} from '@/services/health';
import type { DailyHealthData, DailySummary } from '@/types/health';
import { summarizeHistory } from '@/utils/analytics';

import { useSettingsStore } from './settingsStore';

type Status = 'idle' | 'loading' | 'ready' | 'error';

interface HealthState {
  status: Status;
  error: string | null;
  mode: HealthDataMode | null;
  days: DailyHealthData[];
  summaries: DailySummary[];
  lastUpdated: number | null;
  /** Loads data for the configured (or auto-detected) mode. */
  load: (mode?: HealthDataMode) => Promise<void>;
  /** Re-computes summaries (e.g. after profile changes) without re-reading data. */
  recompute: () => void;
  importFile: () => Promise<{ fileName: string; importedDays: number } | null>;
  deleteLocalData: () => Promise<void>;
}

const messageOf = (e: unknown) => (e instanceof Error ? e.message : 'Unbekannter Fehler');

function summarize(days: DailyHealthData[]) {
  return summarizeHistory(days, useSettingsStore.getState().profile, Date.now());
}

export const useHealthStore = create<HealthState>()((set, get) => ({
  status: 'idle',
  error: null,
  mode: null,
  days: [],
  summaries: [],
  lastUpdated: null,

  load: async (requested) => {
    const settings = useSettingsStore.getState();
    const mode = requested ?? settings.dataMode ?? (await detectDefaultMode());
    if (!settings.dataMode || requested) settings.setDataMode(mode);
    set({ status: 'loading', error: null, mode });
    try {
      const days = await loadHealthDays(mode);
      set({ status: 'ready', days, summaries: summarize(days), lastUpdated: Date.now() });
    } catch (e) {
      set({ status: 'error', error: messageOf(e) });
    }
  },

  recompute: () => {
    const { days } = get();
    set({ summaries: summarize(days) });
  },

  importFile: async () => {
    try {
      const result = await importHealthFile();
      if (!result) return null;
      useSettingsStore.getState().setDataMode('import');
      set({
        mode: 'import',
        status: 'ready',
        error: null,
        days: result.days,
        summaries: summarize(result.days),
        lastUpdated: Date.now(),
      });
      return { fileName: result.fileName, importedDays: result.importedDays };
    } catch (e) {
      set({ error: messageOf(e) });
      throw e;
    }
  },

  deleteLocalData: async () => {
    deleteLocalHealthData();
    await get().load('demo');
  },
}));
