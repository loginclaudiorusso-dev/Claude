/**
 * Claude AI Health & Performance Coach.
 *
 * - `generateDailyBriefing`: structured daily insight (zod-validated JSON)
 * - `CoachChatSession`: streaming chat with read-only tools over local data
 * - `validateApiKey`: checks a key without spending tokens
 *
 * The API key comes exclusively from the Keychain (see coach/apiKeyStore.ts).
 * Requests use `fallbacks: "default"`: if a safety classifier declines, the
 * API transparently re-runs the request on Anthropic's recommended fallback.
 */
import type Anthropic from '@anthropic-ai/sdk';
import { betaZodOutputFormat } from '@anthropic-ai/sdk/helpers/beta/zod';

import type { CoachDailyPayload, CoachInsight } from '@/types/coach';
import type { DayKey } from '@/types/health';

import { getApiKey } from './coach/apiKeyStore';
import { cacheBriefing, getCachedBriefing } from './coach/briefingCache';
import {
  CLAUDE_MODEL,
  CoachError,
  FALLBACK_BETA,
  createClaudeClient,
  toCoachError,
} from './coach/client';
import type { CoachContext } from './coach/context';
import { buildCoachPayload } from './coach/payload';
import { COACH_SYSTEM_PROMPT, briefingUserMessage, chatContextMessage } from './coach/prompts';
import { briefingSchema } from './coach/schema';
import { COACH_TOOLS, executeCoachTool } from './coach/tools';

export { deleteApiKey, getApiKey, hasApiKey, maskApiKey, saveApiKey } from './coach/apiKeyStore';
export { clearBriefingCache } from './coach/briefingCache';
export { CoachError, type CoachErrorKind } from './coach/client';
export type { CoachContext } from './coach/context';
export { buildCoachPayload } from './coach/payload';

const MAX_TOOL_ITERATIONS = 6;
const MAX_RECOMMENDATIONS = 4;

async function requireApiKey(explicit?: string): Promise<string> {
  const key = explicit ?? (await getApiKey());
  if (!key)
    throw new CoachError(
      'missingKey',
      'Hinterlege zuerst deinen Claude API-Key in den Einstellungen.',
    );
  return key;
}

/** djb2 hash – cheap fingerprint to detect whether a cached briefing is stale. */
function fingerprint(payload: CoachDailyPayload): string {
  const s = JSON.stringify(payload);
  let h = 5381;
  for (let i = 0; i < s.length; i++) h = ((h << 5) + h + s.charCodeAt(i)) | 0;
  return `${CLAUDE_MODEL}:${(h >>> 0).toString(36)}`;
}

/** Checks a key with a free Models API call. Resolves on success, throws CoachError otherwise. */
export async function validateApiKey(apiKey: string): Promise<void> {
  try {
    await createClaudeClient(apiKey).models.list({ limit: 1 });
  } catch (error) {
    throw toCoachError(error);
  }
}

export interface BriefingOptions {
  date?: DayKey;
  /** Bypass the on-device cache. */
  force?: boolean;
  apiKey?: string;
}

/**
 * Generates (or returns the cached) daily briefing, e.g.
 * „HRV 12 % unter Schnitt – heute aktiv regenerieren“.
 */
export async function generateDailyBriefing(
  ctx: CoachContext,
  options: BriefingOptions = {},
): Promise<CoachInsight> {
  const payload = buildCoachPayload(ctx, options.date);
  if (!payload)
    throw new CoachError('noData', 'Für diesen Tag liegen noch keine Gesundheitsdaten vor.');
  const fp = fingerprint(payload);
  if (!options.force) {
    const cached = await getCachedBriefing(payload.date, fp);
    if (cached) return cached;
  }

  const client = createClaudeClient(await requireApiKey(options.apiKey));
  let response;
  try {
    response = await client.beta.messages.parse({
      model: CLAUDE_MODEL,
      max_tokens: 16000,
      betas: [FALLBACK_BETA],
      fallbacks: 'default',
      system: COACH_SYSTEM_PROMPT,
      output_config: { format: betaZodOutputFormat(briefingSchema), effort: 'medium' },
      messages: [{ role: 'user', content: briefingUserMessage(JSON.stringify(payload)) }],
    });
  } catch (error) {
    throw toCoachError(error);
  }

  if (response.stop_reason === 'refusal') {
    throw new CoachError('refusal', 'Der Coach konnte zu diesen Daten kein Briefing erstellen.');
  }
  const out = response.parsed_output;
  if (!out || response.stop_reason === 'max_tokens') {
    throw new CoachError(
      'badResponse',
      'Die Antwort des Coaches war unvollständig. Bitte erneut versuchen.',
    );
  }

  const insight: CoachInsight = {
    date: payload.date,
    headline: out.headline.trim(),
    summary: out.summary.trim(),
    focus: out.focus,
    recommendations: out.recommendations
      .map((r) => r.trim())
      .filter(Boolean)
      .slice(0, MAX_RECOMMENDATIONS),
    keyMetric: out.key_metric,
    generatedAt: Date.now(),
  };
  await cacheBriefing(payload.date, fp, insight);
  return insight;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export interface ChatCallbacks {
  /** Full assistant text so far for this turn (not a delta). */
  onText?: (text: string) => void;
  /** Claude is querying local data, e.g. `get_metric_series`. */
  onToolCall?: (toolName: string) => void;
  signal?: AbortSignal;
}

/** Tools with eager input streaming; inputs are validated with zod before running. */
const STREAMING_TOOLS: Anthropic.Beta.BetaTool[] = COACH_TOOLS.map((t) => ({
  ...t,
  eager_input_streaming: true,
}));

/**
 * One conversation with the coach. The API history is kept append-only in
 * memory (including thinking and tool blocks) so earlier turns are never
 * rewritten and the prompt prefix stays cacheable.
 */
export class CoachChatSession {
  private readonly history: Anthropic.Beta.BetaMessageParam[] = [];

  constructor(
    private ctx: CoachContext,
    private readonly apiKey?: string,
  ) {}

  /** Swap in fresh data (e.g. after a HealthKit refresh); applies to future tool calls. */
  updateContext(ctx: CoachContext): void {
    this.ctx = ctx;
  }

  /** True once at least one exchange has happened. */
  get hasHistory(): boolean {
    return this.history.length > 0;
  }

  async send(text: string, { onText, onToolCall, signal }: ChatCallbacks = {}): Promise<string> {
    const client = createClaudeClient(await requireApiKey(this.apiKey));
    const checkpoint = this.history.length;

    const content: Anthropic.Beta.BetaContentBlockParam[] = [];
    if (checkpoint === 0) {
      // Today's snapshot goes into the first turn so it becomes part of the cached prefix.
      const payload = buildCoachPayload(this.ctx);
      if (payload)
        content.push({ type: 'text', text: chatContextMessage(JSON.stringify(payload)) });
    }
    content.push({ type: 'text', text });
    this.history.push({ role: 'user', content });

    let transcript = '';
    try {
      for (let iteration = 0; iteration < MAX_TOOL_ITERATIONS; iteration++) {
        const stream = client.beta.messages.stream(
          {
            model: CLAUDE_MODEL,
            max_tokens: 64000,
            betas: [FALLBACK_BETA],
            fallbacks: 'default',
            system: COACH_SYSTEM_PROMPT,
            tools: STREAMING_TOOLS,
            cache_control: { type: 'ephemeral' },
            output_config: { effort: 'medium' },
            // Snapshot: the history keeps growing while this request is in flight.
            messages: [...this.history],
          },
          { signal },
        );

        const before = transcript;
        let turnText = '';
        for await (const event of stream) {
          if (event.type === 'content_block_start' && event.content_block.type === 'fallback') {
            // A declined model's partial output is superseded by the fallback model.
            turnText = '';
          } else if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
            turnText += event.delta.text;
          } else {
            continue;
          }
          transcript = before && turnText ? `${before}\n\n${turnText}` : before + turnText;
          onText?.(transcript);
        }
        const message = await stream.finalMessage();

        if (message.stop_reason === 'refusal') {
          throw new CoachError('refusal', 'Dazu kann der Coach leider nichts sagen.');
        }
        const toolUses = message.content.filter(
          (b): b is Anthropic.Beta.BetaToolUseBlock => b.type === 'tool_use',
        );
        if (message.stop_reason === 'max_tokens' && toolUses.length > 0) {
          // A truncated tool call can look valid – never run it or keep it in history.
          throw new CoachError(
            'badResponse',
            'Die Antwort des Coaches wurde abgeschnitten. Bitte erneut versuchen.',
          );
        }
        this.history.push({ role: 'assistant', content: message.content });
        if (message.stop_reason !== 'tool_use' || toolUses.length === 0) return transcript;

        const results: Anthropic.Beta.BetaToolResultBlockParam[] = toolUses.map((tool) => {
          onToolCall?.(tool.name);
          const { content: result, isError } = executeCoachTool(tool.name, tool.input, this.ctx);
          return { type: 'tool_result', tool_use_id: tool.id, content: result, is_error: isError };
        });
        this.history.push({ role: 'user', content: results });
      }
      throw new CoachError(
        'badResponse',
        'Der Coach hat zu viele Datenabfragen gebraucht. Bitte präzisiere die Frage.',
      );
    } catch (error) {
      // Drop the failed turn so the next send starts from a valid, unchanged history.
      this.history.length = checkpoint;
      throw toCoachError(error);
    }
  }
}
