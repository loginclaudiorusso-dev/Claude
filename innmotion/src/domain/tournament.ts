// Turnier-Modul: Gruppenphase (jeder gegen jeden) und K.-o.-Runde.
// Tabellen werden immer aus den Spielergebnissen berechnet – nichts wird doppelt gespeichert.

import type { Match, Slot, Tournament, TournamentPlayer } from './types';

export interface TableRow {
  player: TournamentPlayer;
  played: number;
  won: number;
  lost: number;
  scoreFor: number;
  scoreAgainst: number;
  points: number;
  rank: number;
}

export const isPlayed = (m: Match) => m.scoreA !== undefined && m.scoreB !== undefined;

export function groupTable(t: Tournament, group: string): TableRow[] {
  const g = t.groups.find((x) => x.name === group);
  if (!g) return [];
  const rows = new Map<string, TableRow>(
    g.playerIds.map((id) => [
      id,
      { player: t.players.find((p) => p.id === id)!, played: 0, won: 0, lost: 0, scoreFor: 0, scoreAgainst: 0, points: 0, rank: 0 },
    ]),
  );
  for (const m of t.matches) {
    if (m.stage !== 'group' || m.group !== group || !isPlayed(m) || m.a.kind !== 'player' || m.b.kind !== 'player') continue;
    const a = rows.get(m.a.id);
    const b = rows.get(m.b.id);
    if (!a || !b) continue;
    a.played++;
    b.played++;
    a.scoreFor += m.scoreA!;
    a.scoreAgainst += m.scoreB!;
    b.scoreFor += m.scoreB!;
    b.scoreAgainst += m.scoreA!;
    if (m.scoreA! > m.scoreB!) {
      a.won++;
      b.lost++;
      a.points += 2;
    } else if (m.scoreB! > m.scoreA!) {
      b.won++;
      a.lost++;
      b.points += 2;
    } else {
      a.points++;
      b.points++;
    }
  }
  const list = [...rows.values()].sort(
    (x, y) =>
      y.points - x.points ||
      y.scoreFor - y.scoreAgainst - (x.scoreFor - x.scoreAgainst) ||
      y.scoreFor - x.scoreFor ||
      x.player.name.localeCompare(y.player.name),
  );
  list.forEach((r, i) => (r.rank = i + 1));
  return list;
}

export function groupComplete(t: Tournament, group: string): boolean {
  const ms = t.matches.filter((m) => m.stage === 'group' && m.group === group);
  return ms.length > 0 && ms.every(isPlayed);
}

/** Löst einen Platzhalter auf: Spieler-ID, 'bye' (Freilos) oder null (noch offen). */
export function resolveSlot(t: Tournament, slot: Slot): string | 'bye' | null {
  switch (slot.kind) {
    case 'player':
      return slot.id;
    case 'bye':
      return 'bye';
    case 'group':
      return groupComplete(t, slot.group) ? groupTable(t, slot.group)[slot.rank - 1]?.player.id ?? null : null;
    case 'winner': {
      const m = t.matches.find((x) => x.id === slot.match);
      return m ? matchWinner(t, m) : null;
    }
  }
}

export function matchWinner(t: Tournament, m: Match): string | null {
  const a = resolveSlot(t, m.a);
  const b = resolveSlot(t, m.b);
  if (a === 'bye' && b && b !== 'bye') return b;
  if (b === 'bye' && a && a !== 'bye') return a;
  if (!isPlayed(m) || !a || !b || a === 'bye' || b === 'bye') return null;
  if (m.scoreA! === m.scoreB!) return null;
  return m.scoreA! > m.scoreB! ? a : b;
}

export function slotLabel(t: Tournament, slot: Slot): string {
  const r = resolveSlot(t, slot);
  if (r === 'bye') return 'Freilos';
  if (r) return t.players.find((p) => p.id === r)?.name ?? '?';
  if (slot.kind === 'group') return `${slot.rank}. Gruppe ${slot.group}`;
  if (slot.kind === 'winner') {
    const m = t.matches.find((x) => x.id === slot.match);
    return `Sieger ${(m?.label ?? '').replace('Halbfinale', 'HF').replace('Viertelfinale', 'VF')}`.trim();
  }
  return 'offen';
}

export function champion(t: Tournament): string | null {
  const ko = t.matches.filter((m) => m.stage === 'ko');
  if (!ko.length) return null;
  const maxRound = Math.max(...ko.map((m) => m.round ?? 0));
  const final = ko.find((m) => m.round === maxRound);
  return final ? matchWinner(t, final) : null;
}

let counter = 0;
const mid = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${(counter++).toString(36)}`;

/** Jeder gegen jeden innerhalb jeder Gruppe, danach Halbfinale (1A–2B, 1B–2A) und Finale. */
export function buildGroupStage(groups: { name: string; playerIds: string[] }[]): Match[] {
  const matches: Match[] = [];
  for (const g of groups) {
    for (let i = 0; i < g.playerIds.length; i++) {
      for (let j = i + 1; j < g.playerIds.length; j++) {
        matches.push({ id: mid('m'), stage: 'group', group: g.name, a: { kind: 'player', id: g.playerIds[i] }, b: { kind: 'player', id: g.playerIds[j] } });
      }
    }
  }
  if (groups.length === 2) {
    const [A, B] = groups.map((g) => g.name);
    const sf1: Match = { id: mid('ko'), stage: 'ko', round: 1, label: 'Halbfinale 1', a: { kind: 'group', group: A, rank: 1 }, b: { kind: 'group', group: B, rank: 2 } };
    const sf2: Match = { id: mid('ko'), stage: 'ko', round: 1, label: 'Halbfinale 2', a: { kind: 'group', group: B, rank: 1 }, b: { kind: 'group', group: A, rank: 2 } };
    const fin: Match = { id: mid('ko'), stage: 'ko', round: 2, label: 'Finale', a: { kind: 'winner', match: sf1.id }, b: { kind: 'winner', match: sf2.id } };
    matches.push(sf1, sf2, fin);
  } else if (groups.length === 1) {
    const g = groups[0].name;
    matches.push({ id: mid('ko'), stage: 'ko', round: 1, label: 'Finale', a: { kind: 'group', group: g, rank: 1 }, b: { kind: 'group', group: g, rank: 2 } });
  }
  return matches;
}

const ROUND_NAMES: Record<number, string> = { 2: 'Finale', 4: 'Halbfinale', 8: 'Viertelfinale', 16: 'Achtelfinale' };

/** K.-o.-Baum mit Freilosen, falls die Teilnehmerzahl keine Zweierpotenz ist. */
export function buildKnockout(playerIds: string[]): Match[] {
  let size = 2;
  while (size < playerIds.length) size *= 2;
  const slots: Slot[] = Array.from({ length: size }, (_, i) => (playerIds[i] ? { kind: 'player', id: playerIds[i] } : { kind: 'bye' }));
  // Freilose verteilen: Setzliste 1..n gegen n..1
  const ordered: Slot[] = [];
  for (let i = 0; i < size / 2; i++) ordered.push(slots[i], slots[size - 1 - i]);
  const matches: Match[] = [];
  let prev: Match[] = [];
  let round = 1;
  for (let n = size; n >= 2; n /= 2, round++) {
    const current: Match[] = [];
    for (let i = 0; i < n / 2; i++) {
      const a: Slot = round === 1 ? ordered[2 * i] : { kind: 'winner', match: prev[2 * i].id };
      const b: Slot = round === 1 ? ordered[2 * i + 1] : { kind: 'winner', match: prev[2 * i + 1].id };
      const name = ROUND_NAMES[n] ?? `Runde ${round}`;
      current.push({ id: mid('ko'), stage: 'ko', round, label: n / 2 > 1 ? `${name} ${i + 1}` : name, a, b });
    }
    matches.push(...current);
    prev = current;
  }
  return matches;
}

/** Teilnehmende gleichmäßig auf Gruppen verteilen (Schlangen-System). */
export function splitGroups(playerIds: string[], groupCount: number): { name: string; playerIds: string[] }[] {
  const groups = Array.from({ length: groupCount }, (_, i) => ({ name: String.fromCharCode(65 + i), playerIds: [] as string[] }));
  playerIds.forEach((id, i) => {
    const round = Math.floor(i / groupCount);
    const idx = round % 2 === 0 ? i % groupCount : groupCount - 1 - (i % groupCount);
    groups[idx].playerIds.push(id);
  });
  return groups;
}
