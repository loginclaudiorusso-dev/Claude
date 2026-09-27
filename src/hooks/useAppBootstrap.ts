import { useEffect, useSyncExternalStore } from 'react';

import { useCoachStore } from '@/store/coachStore';
import { useHealthStore } from '@/store/healthStore';
import { useSettingsStore } from '@/store/settingsStore';

const subscribeHydration = (onChange: () => void) =>
  useSettingsStore.persist.onFinishHydration(onChange);
const isHydrated = () => useSettingsStore.persist.hasHydrated();

/** Waits for persisted settings, then loads health data and the API-key status once. */
export function useAppBootstrap(): boolean {
  const hydrated = useSyncExternalStore(subscribeHydration, isHydrated, isHydrated);

  useEffect(() => {
    if (!hydrated) return;
    void useHealthStore.getState().load();
    void useCoachStore.getState().refreshKeyStatus();
  }, [hydrated]);

  return hydrated;
}
