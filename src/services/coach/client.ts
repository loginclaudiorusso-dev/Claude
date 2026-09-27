import Anthropic from '@anthropic-ai/sdk';
import { fetch as expoFetch } from 'expo/fetch';
import { Platform } from 'react-native';

import { CLAUDE_MODEL } from '@/config/claude';

export { CLAUDE_MODEL };

/**
 * Server-side refusal fallback: if Claude's safety classifiers decline a
 * request, the API re-runs it on Anthropic's recommended fallback model inside
 * the same call instead of returning a refusal.
 */
export const FALLBACK_BETA = 'server-side-fallback-2026-07-01';

export function createClaudeClient(apiKey: string): Anthropic {
  return new Anthropic({
    apiKey,
    // React Native's built-in fetch cannot stream response bodies; expo/fetch can.
    fetch: Platform.OS === 'web' ? undefined : (expoFetch as unknown as typeof globalThis.fetch),
    // On web the key is typed in by the user themselves and stays in their browser.
    dangerouslyAllowBrowser: Platform.OS === 'web',
    maxRetries: 2,
    timeout: 120_000,
  });
}

export type CoachErrorKind =
  | 'missingKey'
  | 'invalidKey'
  | 'permission'
  | 'rateLimit'
  | 'overloaded'
  | 'network'
  | 'aborted'
  | 'refusal'
  | 'noData'
  | 'badResponse'
  | 'unknown';

export class CoachError extends Error {
  constructor(
    readonly kind: CoachErrorKind,
    message: string,
    readonly cause?: unknown,
  ) {
    super(message);
    this.name = 'CoachError';
  }
}

/** Maps SDK errors (most specific first) to user-facing German messages. */
export function toCoachError(error: unknown): CoachError {
  if (error instanceof CoachError) return error;
  if (error instanceof Anthropic.APIUserAbortError) {
    return new CoachError('aborted', 'Anfrage abgebrochen.', error);
  }
  if (error instanceof Anthropic.AuthenticationError) {
    return new CoachError('invalidKey', 'Der API-Key ist ungültig oder wurde widerrufen.', error);
  }
  if (error instanceof Anthropic.PermissionDeniedError) {
    return new CoachError(
      'permission',
      'Dieser API-Key hat keinen Zugriff auf das gewählte Modell.',
      error,
    );
  }
  if (error instanceof Anthropic.RateLimitError) {
    return new CoachError(
      'rateLimit',
      'Zu viele Anfragen – bitte in einer Minute erneut versuchen.',
      error,
    );
  }
  if (error instanceof Anthropic.APIConnectionError) {
    return new CoachError(
      'network',
      'Keine Verbindung zu Claude. Prüfe deine Internetverbindung.',
      error,
    );
  }
  if (error instanceof Anthropic.APIError && (error.status === 529 || (error.status ?? 0) >= 500)) {
    return new CoachError(
      'overloaded',
      'Claude ist gerade überlastet. Bitte gleich noch einmal versuchen.',
      error,
    );
  }
  if (error instanceof Anthropic.APIError) {
    return new CoachError('unknown', `Claude-Fehler (${error.status ?? '?'}).`, error);
  }
  return new CoachError('unknown', 'Unerwarteter Fehler beim Coach.', error);
}
