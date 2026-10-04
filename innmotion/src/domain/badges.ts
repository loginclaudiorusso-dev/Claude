// Abzeichen werden aus den Daten berechnet (nicht gespeichert) – dadurch immer konsistent.

import { activeSeason, weekStreak } from './league';
import { addDays, startOfWeek } from './time';
import { champion } from './tournament';
import type { DB } from './types';

export interface BadgeDef {
  id: string;
  title: string;
  how: string;
  icon: string;
}

export const BADGES: BadgeDef[] = [
  { id: 'first', title: 'Erster Check-in', how: 'Checke zum ersten Mal ein.', icon: 'Sparkles' },
  { id: 'streak5', title: '5 Wochen am Stück', how: 'Sei 5 Wochen in Folge mindestens einmal aktiv.', icon: 'Flame' },
  { id: 'allrounder', title: 'Allrounder', how: 'Probiere 4 verschiedene Angebote aus.', icon: 'Shapes' },
  { id: 'teamplayer', title: 'Teamplayer', how: 'Checke 5-mal zusammen mit jemandem ein.', icon: 'Users' },
  { id: 'tournament', title: 'Turnier-Teilnahme', how: 'Spiele bei einem Turnier mit.', icon: 'Swords' },
  { id: 'champion', title: 'Turnier-Sieg', how: 'Gewinne ein Turnier.', icon: 'Trophy' },
  { id: 'early', title: 'Frühaufsteher', how: 'Checke 3-mal vor 8 Uhr ein.', icon: 'Sunrise' },
  { id: 'finisher', title: 'Saison-Finisher', how: 'Sei in 6 Wochen der Saison aktiv.', icon: 'Medal' },
];

export function earnedBadges(db: DB, personId: string, now: Date): Set<string> {
  const mine = db.checkins.filter((c) => c.personId === personId && Date.parse(c.at) <= now.getTime());
  const earned = new Set<string>();
  if (mine.length > 0) earned.add('first');

  // Längste Serie (nicht nur die aktuelle)
  const weeks = [...new Set(mine.map((c) => startOfWeek(new Date(c.at)).getTime()))].sort((a, b) => a - b);
  let best = 0;
  let run = 0;
  weeks.forEach((w, i) => {
    run = i > 0 && w - weeks[i - 1] <= 7 * 86_400_000 + 3_600_000 ? run + 1 : 1;
    best = Math.max(best, run);
  });
  if (best >= 5 || weekStreak(mine, personId, now) >= 5) earned.add('streak5');

  if (new Set(mine.map((c) => c.offer)).size >= 4) earned.add('allrounder');
  if (mine.filter((c) => c.buddyId).length >= 5) earned.add('teamplayer');
  if (mine.filter((c) => new Date(c.at).getHours() < 8).length >= 3) earned.add('early');

  for (const t of db.tournaments) {
    const player = t.players.find((p) => p.personId === personId);
    if (!player) continue;
    earned.add('tournament');
    if (champion(t) === player.id) earned.add('champion');
  }

  const season = activeSeason(db) ?? db.seasons[db.seasons.length - 1];
  if (season) {
    const from = startOfWeek(new Date(season.start));
    const to = addDays(new Date(season.end), 1);
    const activeWeeks = new Set(
      mine.filter((c) => Date.parse(c.at) >= from.getTime() && Date.parse(c.at) < to.getTime()).map((c) => startOfWeek(new Date(c.at)).getTime()),
    );
    if (activeWeeks.size >= 6) earned.add('finisher');
  }
  return earned;
}

export function newlyEarned(before: Set<string>, after: Set<string>): BadgeDef[] {
  return BADGES.filter((b) => after.has(b.id) && !before.has(b.id));
}
