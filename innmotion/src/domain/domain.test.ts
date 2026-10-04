import { describe, expect, it } from 'vitest';
import { generateSeed, DEMO_IDS } from '../seed/generate';
import { applyCheckin, evaluateCheckin, resolveCode, LOCK_MS } from './checkin';
import { eventCode, placeCode, qrPayload } from './codes';
import { individualLeaderboard, siteStandings, teamBand } from './league';
import { buildKnockout, champion, groupTable, buildGroupStage } from './tournament';
import { dashboardCsv } from './stats';
import { earnedBadges } from './badges';
import { HOUR, MIN } from './time';
import type { DB } from './types';

const NOW = new Date(2026, 9, 4, 18, 0); // Sonntag, 4. Oktober 2026, 18:00

function checkIn(db: DB, personId: string, raw: string, at: Date) {
  const r = resolveCode(db, personId, raw, at);
  if (!r.ok) return r;
  const e = evaluateCheckin(db, personId, r.value, at);
  if (!e.ok) return e;
  db.checkins = applyCheckin(db.checkins, { id: `t-${at.getTime()}-${personId}`, personId, resolved: r.value, evaluation: e.value, at, source: 'code' });
  return e;
}

describe('Demo-Daten', () => {
  const db = generateSeed(NOW);
  it('hat 3 Standorte mit je 12–18 Teilnehmenden und je 2 Orten', () => {
    expect(db.sites).toHaveLength(3);
    for (const s of db.sites) {
      const n = db.persons.filter((p) => p.role === 'participant' && p.siteId === s.id).length;
      expect(n).toBeGreaterThanOrEqual(12);
      expect(n).toBeLessThanOrEqual(18);
      expect(db.places.filter((p) => p.siteId === s.id)).toHaveLength(2);
    }
  });
  it('hat Check-in-Historie, 6 laufende Challenges, 5 kommende Events, 10 Ideen', () => {
    expect(db.checkins.length).toBeGreaterThan(500);
    const running = db.challenges.filter((c) => Date.parse(c.start) <= NOW.getTime() && Date.parse(c.end) > NOW.getTime());
    expect(running).toHaveLength(6);
    expect(db.events.filter((e) => Date.parse(e.start) > NOW.getTime())).toHaveLength(5);
    expect(db.ideas).toHaveLength(10);
    expect(db.surveys.filter((s) => s.status === 'closed')).toHaveLength(1);
  });
  it('Demo-Person hat genau 2 Aktivitäten in der laufenden Woche', () => {
    const from = new Date(2026, 8, 28);
    expect(db.checkins.filter((c) => c.personId === DEMO_IDS.participant && Date.parse(c.at) >= from.getTime())).toHaveLength(2);
  });
  it('hält überall die Tagesobergrenze ein', () => {
    const perDay = new Map<string, number>();
    for (const c of db.checkins) {
      const k = `${c.personId}|${new Date(c.at).toDateString()}`;
      perDay.set(k, (perDay.get(k) ?? 0) + c.points);
    }
    expect(Math.max(...perDay.values())).toBeLessThanOrEqual(db.settings.dailyPointCap);
  });
});

describe('Check-in-Regeln', () => {
  it('akzeptiert Tagescode und sperrt denselben Ort für 3 Stunden', () => {
    const db = generateSeed(NOW);
    const code = placeCode(db.codeSecret, 'gs-gym', NOW);
    const first = checkIn(db, DEMO_IDS.participant, code, NOW);
    expect(first.ok).toBe(true);
    if (first.ok) expect(first.value.weeklyGoalReached).toBe(true);
    const again = checkIn(db, DEMO_IDS.participant, code, new Date(NOW.getTime() + HOUR));
    expect(again.ok).toBe(false);
    const later = new Date(NOW.getTime() + LOCK_MS + MIN);
    expect(checkIn(db, DEMO_IDS.participant, placeCode(db.codeSecret, 'gs-gym', later), later).ok).toBe(true);
  });
  it('lehnt den Code von gestern ab', () => {
    const db = generateSeed(NOW);
    const yesterday = placeCode(db.codeSecret, 'gs-gym', new Date(NOW.getTime() - 24 * HOUR));
    expect(checkIn(db, DEMO_IDS.participant, yesterday, NOW).ok).toBe(false);
  });
  it('lehnt Codes anderer Standorte ab', () => {
    const db = generateSeed(NOW);
    expect(checkIn(db, DEMO_IDS.participant, placeCode(db.codeSecret, 'we-gym', NOW), NOW).ok).toBe(false);
  });
  it('Event-Codes gelten nur im Event-Zeitraum', () => {
    const db = generateSeed(NOW);
    const ev = db.events.find((e) => e.id === 'ev-rueckenfit')!;
    expect(checkIn(db, DEMO_IDS.participant, eventCode(db.codeSecret, ev.id), NOW).ok).toBe(false);
    expect(checkIn(db, DEMO_IDS.participant, eventCode(db.codeSecret, ev.id), new Date(Date.parse(ev.start) + 10 * MIN)).ok).toBe(true);
  });
  it('abgelaufene QR-Codes werden abgelehnt', () => {
    const db = generateSeed(NOW);
    const old = qrPayload('P', 'gs-gym', placeCode(db.codeSecret, 'gs-gym', NOW), new Date(NOW.getTime() - 10 * MIN));
    expect(checkIn(db, DEMO_IDS.participant, old, NOW).ok).toBe(false);
    const fresh = qrPayload('P', 'gs-gym', placeCode(db.codeSecret, 'gs-gym', NOW), NOW);
    expect(checkIn(db, DEMO_IDS.participant, fresh, NOW).ok).toBe(true);
  });
  it('gibt beiden einen Bonus beim gemeinsamen Check-in', () => {
    const db = generateSeed(NOW);
    const code = placeCode(db.codeSecret, 'gs-gym', NOW);
    db.checkins = db.checkins.filter((c) => !(c.siteId === 'gs' && Date.parse(c.at) > NOW.getTime() - 4 * HOUR));
    checkIn(db, 'p-gs-02', code, NOW);
    const r = checkIn(db, DEMO_IDS.participant, code, new Date(NOW.getTime() + 3 * MIN));
    expect(r.ok && r.value.buddy?.personId).toBe('p-gs-02');
    expect(db.checkins.filter((c) => c.buddyId && Date.parse(c.at) >= NOW.getTime())).toHaveLength(2);
  });
  it('kappt Punkte bei der Tagesobergrenze, zählt die Aktivität aber', () => {
    const db = generateSeed(NOW);
    db.settings.dailyPointCap = 12;
    db.checkins = db.checkins.filter((c) => !(c.personId === DEMO_IDS.participant && new Date(c.at).toDateString() === NOW.toDateString()));
    const r = checkIn(db, DEMO_IDS.participant, placeCode(db.codeSecret, 'gs-gym', NOW), NOW);
    expect(r.ok && r.value.points).toBe(12);
    expect(r.ok && r.value.capped).toBe(true);
  });
});

describe('Demo-Ablauf', () => {
  it('Kalle wird beim Badminton-Treff Allrounder und schafft das Wochenziel', () => {
    for (const day of [4, 5, 6, 7, 8, 9, 10]) {
      const now = new Date(2026, 9, day, 18, 0);
      const db = generateSeed(now);
      const offers = new Set(db.checkins.filter((c) => c.personId === DEMO_IDS.participant).map((c) => c.offer));
      expect([...offers].sort()).toEqual(['Fitnessraum', 'Halle', 'Tischtennis']);
      const r = checkIn(db, DEMO_IDS.participant, eventCode(db.codeSecret, 'ev-badminton'), now);
      expect(r.ok).toBe(true);
      if (r.ok) {
        expect(r.value.newOffer).toBe(true);
        expect(r.value.weeklyGoalReached).toBe(true);
      }
      expect(earnedBadges(db, DEMO_IDS.participant, new Date(now.getTime() + 1)).has('allrounder')).toBe(true);
    }
  });
});

describe('Liga', () => {
  it('rechnet mit Punkten pro aktivem Teilnehmenden', () => {
    const db = generateSeed(NOW);
    db.checkins = [];
    const mk = (personId: string, siteId: string, points: number, i: number) => ({
      id: `x${i}`, personId, siteId, at: NOW.toISOString(), target: { type: 'place' as const, placeId: `${siteId}-gym` }, offer: 'Fitnessraum', points, breakdown: [], source: 'code' as const,
    });
    // Weser-Ems: viele Punkte insgesamt, aber verteilt auf viele Aktive
    db.checkins.push(mk('p-we-01', 'we', 30, 1), mk('p-we-02', 'we', 30, 2), mk('p-we-03', 'we', 30, 3), mk('p-we-04', 'we', 30, 4));
    db.checkins.push(mk('p-bp-01', 'bp', 40, 5), mk('p-bp-02', 'bp', 40, 6));
    const s = siteStandings(db, new Date(NOW.getTime() - HOUR), new Date(NOW.getTime() + HOUR));
    expect(s[0].siteId).toBe('bp');
    expect(s[0].perActive).toBe(40);
    expect(s.find((x) => x.siteId === 'we')!.total).toBe(120);
    expect(s.find((x) => x.siteId === 'we')!.perActive).toBe(30);
  });
  it('Einzel-Rangliste zeigt nur Personen mit Opt-in', () => {
    const db = generateSeed(NOW);
    const rows = individualLeaderboard(db, new Date(0), NOW, 100);
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((r) => r.person.leaderboardOptIn)).toBe(true);
    expect(rows.some((r) => r.person.id === DEMO_IDS.participant)).toBe(false);
  });
  it('Team-Einordnung nennt nie einen letzten Platz', () => {
    const db = generateSeed(NOW);
    for (const p of db.persons.filter((x) => x.role === 'participant')) {
      expect(teamBand(db, p.id, new Date(0), NOW).text).not.toMatch(/letzt/i);
    }
  });
});

describe('Turnier', () => {
  it('berechnet die Gruppentabelle', () => {
    const t = { id: 't', title: 't', sport: 'TT', format: 'groups' as const, status: 'running' as const, scoreUnit: 'Sätze', createdAt: '', players: ['a', 'b', 'c'].map((id) => ({ id, name: id, siteId: 'gs' })), groups: [{ name: 'A', playerIds: ['a', 'b', 'c'] }], matches: buildGroupStage([{ name: 'A', playerIds: ['a', 'b', 'c'] }]) };
    const g = t.matches.filter((m) => m.stage === 'group');
    [g[0].scoreA, g[0].scoreB] = [3, 0]; // a-b
    [g[1].scoreA, g[1].scoreB] = [3, 1]; // a-c
    [g[2].scoreA, g[2].scoreB] = [1, 3]; // b-c
    const table = groupTable(t, 'A');
    expect(table.map((r) => r.player.id)).toEqual(['a', 'c', 'b']);
    expect(table[0].points).toBe(4);
  });
  it('K.-o.-Baum mit Freilos und Sieger', () => {
    const ms = buildKnockout(['a', 'b', 'c']);
    const t = { id: 't', title: 't', sport: 'D', format: 'knockout' as const, status: 'running' as const, scoreUnit: 'Legs', createdAt: '', players: ['a', 'b', 'c'].map((id) => ({ id, name: id, siteId: 'gs' })), groups: [], matches: ms };
    expect(ms).toHaveLength(3);
    const firstRound = ms.filter((m) => m.round === 1);
    const real = firstRound.find((m) => m.a.kind === 'player' && m.b.kind === 'player')!;
    real.scoreA = 3;
    real.scoreB = 1;
    const fin = ms.find((m) => m.round === 2)!;
    fin.scoreA = 0;
    fin.scoreB = 3;
    expect(champion(t)).not.toBeNull();
  });
});

describe('Export', () => {
  it('enthält keine Spitznamen (nur aggregierte Werte)', () => {
    const db = generateSeed(NOW);
    const csv = dashboardCsv(db, 12, NOW);
    expect(csv.startsWith('﻿')).toBe(true);
    for (const p of db.persons.filter((x) => x.role === 'participant')) expect(csv).not.toContain(p.nickname);
  });
});
