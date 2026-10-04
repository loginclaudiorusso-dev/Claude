// Standort-Liga und persönliche Platzierung.
// Fairness: Standort-Wertung = Punkte pro aktivem Teilnehmenden (nicht Gesamtpunkte).

import { addDays, inRange, startOfWeek } from './time';
import type { Checkin, DB, Person, Season } from './types';

export interface SiteStanding {
  siteId: string;
  total: number;
  active: number;
  perActive: number;
  rank: number;
}

const participants = (db: DB) => db.persons.filter((p) => p.role === 'participant');

/** Check-ins von Teilnehmenden im Zeitraum. */
export function checkinsIn(db: DB, from: Date, to: Date): Checkin[] {
  const ids = new Set(participants(db).map((p) => p.id));
  return db.checkins.filter((c) => ids.has(c.personId) && inRange(c.at, from, to));
}

export function siteStandings(db: DB, from: Date, to: Date): SiteStanding[] {
  const list = checkinsIn(db, from, to);
  const rows = db.sites.map((site) => {
    const own = list.filter((c) => c.siteId === site.id);
    const total = own.reduce((s, c) => s + c.points, 0);
    const active = new Set(own.map((c) => c.personId)).size;
    const perActive = active ? Math.round((total / active) * 10) / 10 : 0;
    return { siteId: site.id, total, active, perActive, rank: 0 };
  });
  rows.sort((a, b) => b.perActive - a.perActive || b.active - a.active);
  rows.forEach((r, i) => (r.rank = i > 0 && rows[i - 1].perActive === r.perActive ? rows[i - 1].rank : i + 1));
  return rows;
}

export function activeSeason(db: DB): Season | undefined {
  return db.seasons.find((s) => s.status === 'active');
}

export function seasonRange(season: Season | undefined, now: Date): [Date, Date] {
  if (!season) return [startOfWeek(now), addDays(startOfWeek(now), 7)];
  return [new Date(season.start), new Date(season.end)];
}

/** Kumulierter Saisonverlauf (Punkte pro aktivem TN) je Woche – für das kleine Diagramm. */
export function seasonSeries(db: DB, season: Season, now: Date): { week: Date; values: Record<string, number> }[] {
  const start = startOfWeek(new Date(season.start));
  const end = new Date(Math.min(Date.parse(season.end), now.getTime()));
  const out: { week: Date; values: Record<string, number> }[] = [];
  for (let w = start; w.getTime() <= end.getTime(); w = addDays(w, 7)) {
    const standings = siteStandings(db, new Date(season.start), addDays(w, 7));
    out.push({ week: w, values: Object.fromEntries(standings.map((s) => [s.siteId, s.perActive])) });
  }
  return out;
}

export function personPoints(db: DB, personId: string, from: Date, to: Date): number {
  return db.checkins.filter((c) => c.personId === personId && inRange(c.at, from, to)).reduce((s, c) => s + c.points, 0);
}

export interface LeaderRow {
  person: Person;
  points: number;
  rank: number;
}

/** Einzel-Rangliste: ausschließlich Personen mit Opt-in. Es werden nur die besten `limit` gezeigt – keine letzten Plätze. */
export function individualLeaderboard(db: DB, from: Date, to: Date, limit = 10): LeaderRow[] {
  const rows = participants(db)
    .filter((p) => p.leaderboardOptIn)
    .map((person) => ({ person, points: personPoints(db, person.id, from, to), rank: 0 }))
    .filter((r) => r.points > 0)
    .sort((a, b) => b.points - a.points || a.person.nickname.localeCompare(b.person.nickname));
  rows.forEach((r, i) => (r.rank = i > 0 && rows[i - 1].points === r.points ? rows[i - 1].rank : i + 1));
  return rows.slice(0, limit);
}

export type TeamBand = 'top' | 'upper' | 'active' | 'start';

/** Persönliche Einordnung im eigenen Team – ohne konkreten Platz und ohne „letzter Platz“. */
export function teamBand(db: DB, personId: string, from: Date, to: Date): { band: TeamBand; text: string } {
  const me = db.persons.find((p) => p.id === personId);
  if (!me) return { band: 'start', text: '' };
  const mates = participants(db).filter((p) => p.siteId === me.siteId);
  const scores = mates.map((p) => personPoints(db, p.id, from, to));
  const mine = personPoints(db, personId, from, to);
  if (mine === 0) return { band: 'start', text: 'Mit deinem ersten Check-in bist du dabei.' };
  const better = scores.filter((s) => s > mine).length;
  const share = better / mates.length;
  if (share < 0.25) return { band: 'top', text: 'Du gehörst zum oberen Viertel deines Teams.' };
  if (share < 0.5) return { band: 'upper', text: 'Du bist in der oberen Hälfte deines Teams.' };
  return { band: 'active', text: 'Du bist dabei – jede Aktivität bringt dein Team nach vorn.' };
}

/** Wochen in Folge mit mindestens einer Aktivität (die laufende Woche zählt mit, sobald sie aktiv ist). */
export function weekStreak(checkins: Checkin[], personId: string, now: Date): number {
  const weeks = new Set(checkins.filter((c) => c.personId === personId).map((c) => startOfWeek(new Date(c.at)).getTime()));
  let w = startOfWeek(now);
  if (!weeks.has(w.getTime())) w = addDays(w, -7);
  let n = 0;
  while (weeks.has(w.getTime())) {
    n++;
    w = addDays(w, -7);
  }
  return n;
}
