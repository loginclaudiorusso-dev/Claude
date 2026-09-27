/** Default model for the AI coach; overridable via EXPO_PUBLIC_CLAUDE_MODEL. */
export const CLAUDE_MODEL = process.env.EXPO_PUBLIC_CLAUDE_MODEL ?? 'claude-opus-5';

/** Keychain key under which the user's Anthropic API key is stored (expo-secure-store). */
export const CLAUDE_API_KEY_STORE_KEY = 'pulse.anthropic.apiKey';
