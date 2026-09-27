import { create } from 'zustand';

import {
  CoachChatSession,
  CoachError,
  type CoachContext,
  generateDailyBriefing,
  hasApiKey,
} from '@/services/claudeCoach';
import type { CoachChatMessage, CoachInsight } from '@/types/coach';

type BriefingStatus = 'idle' | 'loading' | 'ready' | 'error';

interface CoachState {
  /** null until checked. */
  hasKey: boolean | null;
  refreshKeyStatus: () => Promise<void>;
  briefing: CoachInsight | null;
  briefingStatus: BriefingStatus;
  briefingError: CoachError | null;
  messages: CoachChatMessage[];
  sending: boolean;
  activeTool: string | null;
  loadBriefing: (ctx: CoachContext, force?: boolean) => Promise<void>;
  send: (text: string, ctx: CoachContext) => Promise<void>;
  cancel: () => void;
  resetChat: () => void;
}

let session: CoachChatSession | null = null;
let abortController: AbortController | null = null;
let idCounter = 0;
const nextId = () => `m${Date.now()}-${idCounter++}`;

const asCoachError = (e: unknown) =>
  e instanceof CoachError ? e : new CoachError('unknown', 'Unerwarteter Fehler beim Coach.', e);

export const useCoachStore = create<CoachState>()((set, get) => ({
  hasKey: null,
  refreshKeyStatus: async () => {
    const hasKey = await hasApiKey();
    set({ hasKey });
    if (!hasKey) set({ briefing: null, briefingStatus: 'idle', briefingError: null });
  },
  briefing: null,
  briefingStatus: 'idle',
  briefingError: null,
  messages: [],
  sending: false,
  activeTool: null,

  loadBriefing: async (ctx, force = false) => {
    if (get().briefingStatus === 'loading') return;
    set({ briefingStatus: 'loading', briefingError: null });
    try {
      const briefing = await generateDailyBriefing(ctx, { force });
      set({ briefing, briefingStatus: 'ready' });
    } catch (e) {
      set({ briefingStatus: 'error', briefingError: asCoachError(e) });
    }
  },

  send: async (text, ctx) => {
    const trimmed = text.trim();
    if (!trimmed || get().sending) return;
    if (!session) session = new CoachChatSession(ctx);
    else session.updateContext(ctx);

    const userMsg: CoachChatMessage = {
      id: nextId(),
      role: 'user',
      text: trimmed,
      createdAt: Date.now(),
    };
    const reply: CoachChatMessage = {
      id: nextId(),
      role: 'assistant',
      text: '',
      createdAt: Date.now(),
      status: 'streaming',
    };
    set((s) => ({ messages: [...s.messages, userMsg, reply], sending: true, activeTool: null }));

    const update = (patch: Partial<CoachChatMessage>) =>
      set((s) => ({
        messages: s.messages.map((m) => (m.id === reply.id ? { ...m, ...patch } : m)),
      }));

    abortController = new AbortController();
    try {
      const final = await session.send(trimmed, {
        signal: abortController.signal,
        onText: (t) =>
          set((s) => ({
            activeTool: null,
            messages: s.messages.map((m) => (m.id === reply.id ? { ...m, text: t } : m)),
          })),
        onToolCall: (name) => set({ activeTool: name }),
      });
      update({ text: final, status: 'done' });
    } catch (e) {
      const err = asCoachError(e);
      if (err.kind === 'aborted')
        update({
          status: 'done',
          text: get().messages.find((m) => m.id === reply.id)?.text || 'Abgebrochen.',
        });
      else update({ status: 'error', text: err.message });
    } finally {
      abortController = null;
      set({ sending: false, activeTool: null });
    }
  },

  cancel: () => abortController?.abort(),

  resetChat: () => {
    abortController?.abort();
    session = null;
    set({ messages: [], sending: false, activeTool: null });
  },
}));
