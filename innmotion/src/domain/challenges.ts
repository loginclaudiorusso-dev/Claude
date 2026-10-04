// Fortschritt von Challenges – persönlich (Woche/Saison) oder für das Standort-Team.

import { addDays, inRange, startOfWeek } from './time';
import type { Challenge, DB } from './types';

export type ChallengeStatus = 'bald' | 'offen' | 'läuft' | 'geschafft' | 'beendet';

export interface ChallengeProgress {
  challenge: Challenge;
  current: number;
  target: number;
  status: ChallengeStatus;
}

export function challengeTarget(c: Challenge, siteId: string): number {
  return c.targetBySite?.[siteId] ?? c.target;
}

export function challengeProgress(db: DB, c: Challenge, personId: string, now: Date): ChallengeProgress {
  const person = db.persons.find((p) => p.id === personId);
  const siteId = person?.siteId ?? '';
  const from = new Date(c.start);
  const to = new Date(c.end);
  const target = challengeTarget(c, siteId);
  const mine = db.checkins.filter((ch) => ch.personId === personId);
  const mineIn = mine.filter((ch) => inRange(ch.at, from, to));
  const participantIds = new Set(db.persons.filter((p) => p.role === 'participant' && p.siteId === siteId).map((p) => p.id));
  const teamIn = db.checkins.filter((ch) => participantIds.has(ch.personId) && inRange(ch.at, from, to));

  let current = 0;
  switch (c.metric) {
    case 'activities':
      current = mineIn.length;
      break;
    case 'newOffer': {
      const before = new Set(mine.filter((ch) => Date.parse(ch.at) < from.getTime()).map((ch) => ch.offer));
      current = new Set(mineIn.filter((ch) => !before.has(ch.offer)).map((ch) => ch.offer)).size;
      break;
    }
    case 'buddy':
      current = mineIn.filter((ch) => ch.buddyId).length;
      break;
    case 'teamCheckins':
      current = teamIn.length;
      break;
    case 'teamEvents':
      current = teamIn.filter((ch) => ch.target.type === 'event').length;
      break;
    case 'activeWeeks': {
      const perWeek = new Map<number, number>();
      for (const ch of mineIn) {
        const w = startOfWeek(new Date(ch.at)).getTime();
        perWeek.set(w, (perWeek.get(w) ?? 0) + 1);
      }
      current = [...perWeek.values()].filter((n) => n >= 2).length;
      break;
    }
  }

  let status: ChallengeStatus;
  if (now.getTime() < from.getTime()) status = 'bald';
  else if (current >= target) status = 'geschafft';
  else if (now.getTime() >= to.getTime()) status = 'beendet';
  else status = current > 0 ? 'läuft' : 'offen';
  return { challenge: c, current: Math.min(current, target), target, status };
}

/** Wochen-Challenges laufen automatisch jede Woche neu: Zeitraum auf die aktuelle Woche setzen. */
export function currentWindow(c: Challenge, now: Date): Challenge {
  if (c.scope !== 'week') return c;
  const from = startOfWeek(now);
  return { ...c, start: from.toISOString(), end: addDays(from, 7).toISOString() };
}

export const STATUS_LABEL: Record<ChallengeStatus, string> = {
  bald: 'Startet bald',
  offen: 'Offen',
  läuft: 'Läuft',
  geschafft: 'Geschafft',
  beendet: 'Beendet',
};
