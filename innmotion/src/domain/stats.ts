// Kennzahlen für das Leitungs-Dashboard. Ausschließlich aggregierte Werte – keine Einzelpersonen.

import { checkinsIn } from './league';
import { addDays, dayKey, isoWeek, weekStarts } from './time';
import type { DB } from './types';

export interface WeekKpis {
  siteId: string;
  week: Date;
  active: number;
  occupancy: number;
  rate: number;
  checkins: number;
  byOffer: Record<string, number>;
  events: number;
  eventSeats: number;
  eventRegistered: number;
  eventUtilisation: number;
}

export function weekKpis(db: DB, siteId: string, week: Date): WeekKpis {
  const to = addDays(week, 7);
  const list = checkinsIn(db, week, to).filter((c) => c.siteId === siteId);
  const site = db.sites.find((s) => s.id === siteId)!;
  const active = new Set(list.map((c) => c.personId)).size;
  const byOffer: Record<string, number> = {};
  for (const c of list) byOffer[c.offer] = (byOffer[c.offer] ?? 0) + 1;
  const events = db.events.filter((e) => e.siteId === siteId && Date.parse(e.start) >= week.getTime() && Date.parse(e.start) < to.getTime());
  const eventSeats = events.reduce((s, e) => s + e.capacity, 0);
  const eventRegistered = events.reduce((s, e) => s + Math.min(e.capacity, e.registered.length), 0);
  return {
    siteId,
    week,
    active,
    occupancy: site.occupancy,
    rate: site.occupancy ? active / site.occupancy : 0,
    checkins: list.length,
    byOffer,
    events: events.length,
    eventSeats,
    eventRegistered,
    eventUtilisation: eventSeats ? eventRegistered / eventSeats : 0,
  };
}

export function kpiSeries(db: DB, siteId: string, weeks: number, now: Date): WeekKpis[] {
  return weekStarts(weeks, now).map((w) => weekKpis(db, siteId, w));
}

export function popularOffers(db: DB, from: Date, to: Date, siteId?: string): { offer: string; count: number }[] {
  const map = new Map<string, number>();
  for (const c of checkinsIn(db, from, to)) {
    if (siteId && c.siteId !== siteId) continue;
    map.set(c.offer, (map.get(c.offer) ?? 0) + 1);
  }
  return [...map.entries()].map(([offer, count]) => ({ offer, count })).sort((a, b) => b.count - a.count);
}

export interface SurveyStat {
  questionId: string;
  text: string;
  avg: number;
  count: number;
  bySite: Record<string, number>;
  distribution: number[];
}

export function surveyStats(db: DB, surveyId: string): { responses: number; questions: SurveyStat[]; comments: string[] } {
  const survey = db.surveys.find((s) => s.id === surveyId);
  if (!survey) return { responses: 0, questions: [], comments: [] };
  const rs = db.surveyResponses.filter((r) => r.surveyId === surveyId);
  const avg = (xs: number[]) => (xs.length ? Math.round((xs.reduce((a, b) => a + b, 0) / xs.length) * 10) / 10 : 0);
  const questions = survey.questions.map((q) => {
    const vals = rs.map((r) => r.answers[q.id]).filter((v): v is number => typeof v === 'number');
    const bySite: Record<string, number> = {};
    for (const site of db.sites) bySite[site.id] = avg(rs.filter((r) => r.siteId === site.id).map((r) => r.answers[q.id]).filter((v) => typeof v === 'number'));
    const distribution = [1, 2, 3, 4, 5].map((n) => vals.filter((v) => v === n).length);
    return { questionId: q.id, text: q.text, avg: avg(vals), count: vals.length, bySite, distribution };
  });
  const comments = [...new Set(rs.flatMap((r) => Object.values(r.comments)).filter((c) => c.trim().length > 0))];
  return { responses: rs.length, questions, comments };
}

/** CSV mit Semikolon und BOM – öffnet sich in deutschem Excel direkt korrekt. */
export function toCsv(rows: (string | number)[][]): string {
  const esc = (v: string | number) => {
    const s = typeof v === 'number' ? String(v).replace('.', ',') : v;
    return /[;"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return '﻿' + rows.map((r) => r.map(esc).join(';')).join('\r\n');
}

export function dashboardCsv(db: DB, weeks: number, now: Date): string {
  const header = ['Woche', 'Wochenbeginn', 'Standort', 'Aktive Teilnehmende', 'Belegung', 'Teilnahmequote %', 'Check-ins', 'Events', 'Event-Auslastung %'];
  const offers = [...new Set(db.checkins.map((c) => c.offer))].sort();
  const rows: (string | number)[][] = [[...header, ...offers.map((o) => `Check-ins ${o}`)]];
  for (const w of weekStarts(weeks, now)) {
    for (const site of db.sites) {
      const k = weekKpis(db, site.id, w);
      rows.push([
        `KW ${isoWeek(w)}`,
        dayKey(w),
        site.name,
        k.active,
        k.occupancy,
        Math.round(k.rate * 1000) / 10,
        k.checkins,
        k.events,
        Math.round(k.eventUtilisation * 1000) / 10,
        ...offers.map((o) => k.byOffer[o] ?? 0),
      ]);
    }
  }
  return toCsv(rows);
}
