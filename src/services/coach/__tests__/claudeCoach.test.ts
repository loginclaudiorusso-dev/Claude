import { generateDemoDays } from '@/services/health/demoData';
import { summarizeHistory } from '@/utils/analytics';

import type { CoachContext } from '../context';

jest.mock('../apiKeyStore', () => ({
  getApiKey: jest.fn(async () => 'sk-ant-test-key-000000000000000000'),
}));
jest.mock('../briefingCache', () => ({
  getCachedBriefing: jest.fn(async () => null),
  cacheBriefing: jest.fn(async () => {}),
}));

const mockClient = {
  beta: { messages: { stream: jest.fn(), parse: jest.fn() } },
  models: { list: jest.fn() },
};
jest.mock('../client', () => ({
  ...jest.requireActual('../client'),
  createClaudeClient: () => mockClient,
}));

// Imported after mocks are registered.
// eslint-disable-next-line import/first
import { CoachChatSession, CoachError, generateDailyBriefing } from '../../claudeCoach';

type Block = Record<string, unknown>;

/** Fake SDK stream: yields events, resolves `finalMessage()`. */
function fakeStream(events: Block[], finalMessage: Block) {
  return {
    async *[Symbol.asyncIterator]() {
      for (const e of events) yield e;
    },
    finalMessage: async () => finalMessage,
  };
}

const text = (t: string) => ({
  type: 'content_block_delta',
  delta: { type: 'text_delta', text: t },
});

const now = new Date(2026, 8, 20, 15, 0).getTime();
const days = generateDemoDays(30, now);
const ctx: CoachContext = { days, summaries: summarizeHistory(days, {}, now) };

beforeEach(() => jest.clearAllMocks());

describe('CoachChatSession', () => {
  it('runs local tools and streams the final answer', async () => {
    mockClient.beta.messages.stream
      .mockReturnValueOnce(
        fakeStream([text('Ich schaue nach…')], {
          stop_reason: 'tool_use',
          content: [
            { type: 'text', text: 'Ich schaue nach…' },
            {
              type: 'tool_use',
              id: 't1',
              name: 'compare_after_training',
              input: { metric: 'sleep_score', days: 30 },
            },
          ],
        }),
      )
      .mockReturnValueOnce(
        fakeStream([text('Nach Trainingstagen schläfst du besser.')], {
          stop_reason: 'end_turn',
          content: [{ type: 'text', text: 'Nach Trainingstagen schläfst du besser.' }],
        }),
      );

    const session = new CoachChatSession(ctx);
    const updates: string[] = [];
    const tools: string[] = [];
    const answer = await session.send('Wie schlafe ich nach dem Training?', {
      onText: (t) => updates.push(t),
      onToolCall: (n) => tools.push(n),
    });

    expect(answer).toBe('Ich schaue nach…\n\nNach Trainingstagen schläfst du besser.');
    expect(updates.at(-1)).toBe(answer);
    expect(tools).toEqual(['compare_after_training']);

    const [firstCall] = mockClient.beta.messages.stream.mock.calls;
    const params = firstCall[0];
    expect(params).toMatchObject({
      fallbacks: 'default',
      betas: ['server-side-fallback-2026-07-01'],
    });
    expect(params.tools.every((t: Block) => t.eager_input_streaming === true)).toBe(true);
    // First user turn carries today's data as context.
    expect(params.messages[0].content[0].text).toContain('<tagesdaten>');

    const second = mockClient.beta.messages.stream.mock.calls[1][0];
    const toolResult = second.messages.at(-1).content[0];
    expect(toolResult).toMatchObject({ type: 'tool_result', tool_use_id: 't1', is_error: false });
    expect(JSON.parse(toolResult.content).afterTraining.days).toBeGreaterThan(0);
  });

  it('drops partial output when a fallback model takes over', async () => {
    mockClient.beta.messages.stream.mockReturnValueOnce(
      fakeStream(
        [
          text('Teil'),
          { type: 'content_block_start', content_block: { type: 'fallback' } },
          text('Neu'),
        ],
        { stop_reason: 'end_turn', content: [{ type: 'text', text: 'Neu' }] },
      ),
    );
    expect(await new CoachChatSession(ctx).send('Hi')).toBe('Neu');
  });

  it('rolls back history on refusal and truncated tool calls', async () => {
    const session = new CoachChatSession(ctx);
    mockClient.beta.messages.stream.mockReturnValueOnce(
      fakeStream([], { stop_reason: 'refusal', content: [] }),
    );
    await expect(session.send('x')).rejects.toMatchObject({ kind: 'refusal' });
    expect(session.hasHistory).toBe(false);

    mockClient.beta.messages.stream.mockReturnValueOnce(
      fakeStream([], {
        stop_reason: 'max_tokens',
        content: [{ type: 'tool_use', id: 't', name: 'list_workouts', input: { days: 7 } }],
      }),
    );
    await expect(session.send('y')).rejects.toBeInstanceOf(CoachError);
    expect(session.hasHistory).toBe(false);
  });
});

describe('generateDailyBriefing', () => {
  it('returns a trimmed insight from structured output', async () => {
    mockClient.beta.messages.parse.mockResolvedValueOnce({
      stop_reason: 'end_turn',
      parsed_output: {
        headline: ' HRV 12 % unter Schnitt – heute regenerieren ',
        summary: 'Kurz.',
        focus: 'recover',
        recommendations: ['a', 'b', 'c', 'd', 'e', ' '],
        key_metric: 'hrv',
      },
    });
    const insight = await generateDailyBriefing(ctx, { force: true });
    expect(insight.headline).toBe('HRV 12 % unter Schnitt – heute regenerieren');
    expect(insight.recommendations).toEqual(['a', 'b', 'c', 'd']);
    expect(insight.date).toBe('2026-09-20');
    expect(mockClient.beta.messages.parse.mock.calls[0][0].output_config.effort).toBe('medium');
  });

  it('maps refusals and missing data to CoachErrors', async () => {
    mockClient.beta.messages.parse.mockResolvedValueOnce({
      stop_reason: 'refusal',
      parsed_output: null,
    });
    await expect(generateDailyBriefing(ctx, { force: true })).rejects.toMatchObject({
      kind: 'refusal',
    });
    await expect(generateDailyBriefing({ days: [], summaries: [] })).rejects.toMatchObject({
      kind: 'noData',
    });
  });
});
