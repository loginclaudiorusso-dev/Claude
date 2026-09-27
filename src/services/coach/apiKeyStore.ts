import * as SecureStore from 'expo-secure-store';

import { CLAUDE_API_KEY_STORE_KEY } from '@/config/claude';

/**
 * The Anthropic API key lives only in the iOS Keychain / Android Keystore via
 * expo-secure-store: available after unlock, never synced to other devices,
 * never written to AsyncStorage, files or logs.
 */
const OPTIONS: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
};

export function looksLikeAnthropicKey(key: string): boolean {
  return /^sk-ant-[A-Za-z0-9_-]{20,}$/.test(key.trim());
}

export async function getApiKey(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(CLAUDE_API_KEY_STORE_KEY, OPTIONS);
  } catch {
    // SecureStore is unavailable on web; the coach then shows its "add key" state.
    return null;
  }
}

export async function hasApiKey(): Promise<boolean> {
  return (await getApiKey()) !== null;
}

export async function saveApiKey(key: string): Promise<void> {
  const trimmed = key.trim();
  if (!looksLikeAnthropicKey(trimmed))
    throw new Error('Das sieht nicht nach einem Anthropic API-Key aus (sk-ant-…).');
  await SecureStore.setItemAsync(CLAUDE_API_KEY_STORE_KEY, trimmed, OPTIONS);
}

export async function deleteApiKey(): Promise<void> {
  await SecureStore.deleteItemAsync(CLAUDE_API_KEY_STORE_KEY, OPTIONS);
}

/** "sk-ant-…a1B2" – safe to show in the UI. */
export function maskApiKey(key: string): string {
  return `${key.slice(0, 7)}…${key.slice(-4)}`;
}
