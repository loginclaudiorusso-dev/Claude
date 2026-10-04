// Check-in-Regeln. Reine Funktionen – keine React-, Browser- oder Speicher-Abhängigkeiten.
//
// Punkte: Mitmachen zählt mehr als Leistung.
//   Fitnessraum/Halle 10 · Event laut Event (Standard 15, Turnier 20)
//   + 5 beim ersten Mal in einem neuen Angebot
//   + 5 je Person, wenn zwei Personen innerhalb von 10 Minuten am gleichen Ort einchecken
//   + 10, wenn mit diesem Check-in das Wochenziel erreicht wird
// Schutz gegen Mehrfach-Punkte:
//   pro Ort/Event höchstens ein Check-in je 3 Stunden, Tagesobergrenze (Standard 40),
//   Event-Codes nur im Event-Zeitraum, Raum-Codes wechseln täglich.

import { eventCode, parseCode, placeCode, rotationSlot, ROTATION_TOLERANCE } from './codes';
import { dayKey, fmt, HOUR, MIN, startOfWeek, addDays, inRange } from './time';
import type { Checkin, CheckinTarget, DB, PointItem, SportEvent } from './types';

export const POINTS = {
  place: 10,
  newOffer: 5,
  buddy: 5,
  weeklyGoal: 10,
} as const;

export const LOCK_MS = 3 * HOUR;
export const BUDDY_WINDOW_MS = 10 * MIN;
/** Event-Codes gelten ab 30 Minuten vor Beginn bis zum Ende. */
export const EVENT_EARLY_MS = 30 * MIN;

const OFFER_BY_KIND = { gym: 'Fitnessraum', hall: 'Halle' } as const;

export interface ResolvedTarget {
  target: CheckinTarget;
  siteId: string;
  offer: string;
  label: string;
  basePoints: number;
}

export type Result<T> = { ok: true; value: T } | { ok: false; reason: string };

const fail = (reason: string): { ok: false; reason: string } => ({ ok: false, reason });

export function eventWindowOpen(ev: SportEvent, now: Date): boolean {
  return now.getTime() >= Date.parse(ev.start) - EVENT_EARLY_MS && now.getTime() <= Date.parse(ev.end);
}

/** Wandelt einen gescannten oder eingetippten Code in ein Check-in-Ziel um. */
export function resolveCode(db: DB, personId: string, raw: string, now: Date): Result<ResolvedTarget> {
  const person = db.persons.find((p) => p.id === personId);
  if (!person) return fail('Person nicht gefunden.');
  const parsed = parseCode(raw);
  if (parsed.kind === 'invalid') {
    return fail('Das ist kein gültiger Check-in-Code. Ein Code hat 6 Zeichen, z. B. „K7Q 2MX“.');
  }

  const placeTarget = (placeId: string): Result<ResolvedTarget> => {
    const place = db.places.find((p) => p.id === placeId && p.active);
    if (!place) return fail('Diesen Ort gibt es nicht (mehr).');
    if (place.siteId !== person.siteId) return fail('Dieser Code gehört zu einem anderen Standort.');
    return {
      ok: true,
      value: {
        target: { type: 'place', placeId: place.id },
        siteId: place.siteId,
        offer: OFFER_BY_KIND[place.kind],
        label: place.name,
        basePoints: POINTS.place,
      },
    };
  };

  const eventTarget = (ev: SportEvent): Result<ResolvedTarget> => {
    if (ev.siteId !== person.siteId) return fail('Dieses Event findet an einem anderen Standort statt.');
    if (now.getTime() < Date.parse(ev.start) - EVENT_EARLY_MS) {
      return fail(`Der Code für „${ev.title}“ gilt erst ab ${fmt.time(Date.parse(ev.start) - EVENT_EARLY_MS)} Uhr.`);
    }
    if (now.getTime() > Date.parse(ev.end)) return fail(`„${ev.title}“ ist schon vorbei. Der Code gilt nicht mehr.`);
    return {
      ok: true,
      value: {
        target: { type: 'event', eventId: ev.id },
        siteId: ev.siteId,
        offer: ev.sport,
        label: ev.title,
        basePoints: ev.points,
      },
    };
  };

  if (parsed.kind === 'P' || parsed.kind === 'E') {
    if (Math.abs(rotationSlot(now) - parsed.slot) > ROTATION_TOLERANCE) {
      return fail('Dieser QR-Code ist abgelaufen. Bitte scanne den aktuellen Code direkt vor Ort.');
    }
    if (parsed.kind === 'P') {
      if (placeCode(db.codeSecret, parsed.id, now) !== parsed.code) {
        return fail('Dieser Raum-Code ist nicht von heute. Raum-Codes wechseln jeden Tag.');
      }
      return placeTarget(parsed.id);
    }
    const ev = db.events.find((e) => e.id === parsed.id);
    if (!ev || eventCode(db.codeSecret, ev.id) !== parsed.code) return fail('Diesen Event-Code kennen wir nicht.');
    return eventTarget(ev);
  }

  // Manuelle Eingabe: Tagescodes der Orte des eigenen Standorts und Event-Codes prüfen.
  for (const place of db.places) {
    if (place.active && placeCode(db.codeSecret, place.id, now) === parsed.code) return placeTarget(place.id);
  }
  for (const ev of db.events) {
    if (eventCode(db.codeSecret, ev.id) === parsed.code) return eventTarget(ev);
  }
  return fail('Diesen Code kennen wir nicht. Raum-Codes wechseln täglich – schau auf den aktuellen Aushang.');
}

export const sameTarget = (a: CheckinTarget, b: CheckinTarget) =>
  a.type === b.type && (a.type === 'place' ? a.placeId === (b as typeof a).placeId : a.eventId === (b as { eventId: string }).eventId);

export function pointsOnDay(checkins: Checkin[], personId: string, day: string): number {
  return checkins.filter((c) => c.personId === personId && dayKey(c.at) === day).reduce((s, c) => s + c.points, 0);
}

export function activitiesInWeek(checkins: Checkin[], personId: string, at: Date): number {
  const from = startOfWeek(at);
  const to = addDays(from, 7);
  return checkins.filter((c) => c.personId === personId && inRange(c.at, from, to)).length;
}

export interface Evaluation {
  points: number;
  breakdown: PointItem[];
  buddy?: { checkinId: string; personId: string; bonus: number };
  weeklyGoalReached: boolean;
  newOffer: boolean;
  capped: boolean;
}

/** Prüft Sperren und berechnet die Punkte für einen Check-in. */
export function evaluateCheckin(db: DB, personId: string, resolved: ResolvedTarget, now: Date): Result<Evaluation> {
  const mine = db.checkins.filter((c) => c.personId === personId);

  const recent = mine
    .filter((c) => sameTarget(c.target, resolved.target) && now.getTime() - Date.parse(c.at) < LOCK_MS && Date.parse(c.at) <= now.getTime())
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
  if (recent) {
    const next = Date.parse(recent.at) + LOCK_MS;
    return fail(
      `Du bist hier schon seit ${fmt.time(recent.at)} Uhr eingecheckt. Der nächste Check-in an diesem Ort geht ab ${fmt.time(next)} Uhr.`,
    );
  }

  const breakdown: PointItem[] = [{ label: resolved.target.type === 'event' ? 'Event-Teilnahme' : 'Check-in', points: resolved.basePoints }];

  const newOffer = !mine.some((c) => c.offer === resolved.offer);
  if (newOffer) breakdown.push({ label: `Neues Angebot: ${resolved.offer}`, points: POINTS.newOffer });

  const buddyCheckin = db.checkins
    .filter(
      (c) =>
        c.personId !== personId &&
        !c.buddyId &&
        c.siteId === resolved.siteId &&
        sameTarget(c.target, resolved.target) &&
        now.getTime() - Date.parse(c.at) <= BUDDY_WINDOW_MS &&
        Date.parse(c.at) <= now.getTime(),
    )
    .sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
  if (buddyCheckin) breakdown.push({ label: 'Zu zweit eingecheckt', points: POINTS.buddy });

  const weekly = activitiesInWeek(db.checkins, personId, now);
  const weeklyGoalReached = weekly + 1 === db.settings.weeklyGoal;
  if (weeklyGoalReached) breakdown.push({ label: 'Wochenziel geschafft', points: POINTS.weeklyGoal });

  const raw = breakdown.reduce((s, b) => s + b.points, 0);
  const today = pointsOnDay(db.checkins, personId, dayKey(now));
  const room = Math.max(0, db.settings.dailyPointCap - today);
  const points = Math.min(raw, room);
  const capped = points < raw;
  if (capped) breakdown.push({ label: 'Tagesobergrenze erreicht', points: points - raw });

  let buddy: Evaluation['buddy'];
  if (buddyCheckin) {
    const buddyRoom = Math.max(0, db.settings.dailyPointCap - pointsOnDay(db.checkins, buddyCheckin.personId, dayKey(now)));
    buddy = { checkinId: buddyCheckin.id, personId: buddyCheckin.personId, bonus: Math.min(POINTS.buddy, buddyRoom) };
  }

  return { ok: true, value: { points, breakdown, buddy, weeklyGoalReached, newOffer, capped } };
}

/** Wendet eine Bewertung an und liefert die neue Check-in-Liste (immutabel). */
export function applyCheckin(
  checkins: Checkin[],
  input: { id: string; personId: string; resolved: ResolvedTarget; evaluation: Evaluation; at: Date; source: Checkin['source'] },
): Checkin[] {
  const { resolved, evaluation } = input;
  const created: Checkin = {
    id: input.id,
    personId: input.personId,
    siteId: resolved.siteId,
    at: input.at.toISOString(),
    target: resolved.target,
    offer: resolved.offer,
    points: evaluation.points,
    breakdown: evaluation.breakdown,
    buddyId: evaluation.buddy?.personId,
    source: input.source,
  };
  const updated = evaluation.buddy
    ? checkins.map((c) =>
        c.id === evaluation.buddy!.checkinId
          ? {
              ...c,
              buddyId: input.personId,
              points: c.points + evaluation.buddy!.bonus,
              breakdown: [...c.breakdown, { label: 'Zu zweit eingecheckt', points: evaluation.buddy!.bonus }],
            }
          : c,
      )
    : checkins;
  return [...updated, created];
}
