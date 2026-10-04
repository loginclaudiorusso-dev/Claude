// Demo-Daten-Generator. Alle Namen und Werte sind frei erfunden.
// Deterministisch (fester Zufalls-Seed), relativ zum aktuellen Datum, damit die Demo immer „frisch“ wirkt.

import { applyCheckin, evaluateCheckin, type ResolvedTarget } from '../domain/checkin';
import { buildGroupStage, buildKnockout } from '../domain/tournament';
import { addDays, DAY, HOUR, MIN, startOfWeek } from '../domain/time';
import type {
  Announcement,
  AppNotification,
  Challenge,
  CheckinTarget,
  DB,
  Idea,
  Person,
  Place,
  Season,
  Site,
  SportEvent,
  Survey,
  SurveyResponse,
  Tournament,
} from '../domain/types';

export const DB_VERSION = 3;
export const HISTORY_WEEKS = 12;

export const DEMO_IDS = {
  participant: 'p-gs-01',
  staff: 's-gs',
  lead: 'lead',
} as const;

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const NICKNAMES: Record<string, string[]> = {
  gs: ['Kalle', 'Sunny', 'Mo', 'Jojo', 'Tine', 'Rocky', 'Pia', 'Ole', 'Fritzi', 'Nele', 'Ali', 'Mira', 'Leo', 'Hanne', 'Can', 'Bea'],
  we: ['Ben', 'Lu', 'Dani', 'Kai', 'Tom', 'Sam', 'Jule', 'Ivo', 'Ronja', 'Paul', 'Ella', 'Timo', 'Zoe', 'Finn', 'Lotte', 'Maxi', 'Robin', 'Emre'],
  bp: ['Lina', 'Jan', 'Kim', 'Uwe', 'Sina', 'Noah', 'Ayla', 'Hugo', 'Greta', 'Erik', 'Tara', 'Rafi'],
};

const SUBGROUPS = ['Haus A · EG', 'Haus A · 1. OG', 'Haus B · EG', 'Haus B · 1. OG', 'Haus C'];

export function generateSeed(now = new Date()): DB {
  const rnd = mulberry32(20261004);
  const pick = <T,>(xs: T[]) => xs[Math.floor(rnd() * xs.length)];
  const between = (a: number, b: number) => a + rnd() * (b - a);
  const poisson = (lambda: number) => {
    const L = Math.exp(-lambda);
    let k = 0;
    let p = 1;
    do {
      k++;
      p *= rnd();
    } while (p > L);
    return k - 1;
  };

  const thisWeek = startOfWeek(now);
  const historyStart = addDays(thisWeek, -7 * (HISTORY_WEEKS - 1));

  const sites: Site[] = [
    { id: 'gs', name: 'Goslar', short: 'GS', team: 'gs', teamName: 'Team Goslar', occupancy: 24 },
    { id: 'we', name: 'Weser-Ems', short: 'WE', team: 'we', teamName: 'Team Weser-Ems', occupancy: 30 },
    { id: 'bp', name: 'Bad Pyrmont', short: 'BP', team: 'bp', teamName: 'Team Bad Pyrmont', occupancy: 17 },
  ];

  const places: Place[] = sites.flatMap((s) => [
    { id: `${s.id}-gym`, siteId: s.id, name: 'Fitnessraum', kind: 'gym' as const, active: true },
    { id: `${s.id}-hall`, siteId: s.id, name: 'Sporthalle', kind: 'hall' as const, active: true },
  ]);

  // Personen ---------------------------------------------------------------
  const persons: Person[] = [];
  const propensity = new Map<string, number>();
  const siteFactor: Record<string, number> = { gs: 1.12, we: 0.86, bp: 1.12 };
  for (const site of sites) {
    NICKNAMES[site.id].forEach((nickname, i) => {
      const id = `p-${site.id}-${String(i + 1).padStart(2, '0')}`;
      const joinedWeeksAgo = i % 5 === 3 ? Math.floor(between(2, 6)) : Math.floor(between(13, 30));
      const joinedAt = addDays(thisWeek, -7 * joinedWeeksAgo + Math.floor(between(0, 5)));
      persons.push({
        id,
        nickname,
        role: 'participant',
        siteId: site.id,
        subgroup: rnd() < 0.7 ? pick(SUBGROUPS) : undefined,
        leaderboardOptIn: id === DEMO_IDS.participant ? false : rnd() < 0.45,
        notifications: rnd() < 0.8,
        joinedAt: joinedAt.toISOString(),
        programEnd: addDays(joinedAt, Math.floor(between(150, 330))).toISOString(),
        surveysAnswered: [],
      });
      // Unterschiedliche Voraussetzungen: einige sehr aktiv, viele gelegentlich, wenige gar nicht.
      const r = rnd();
      propensity.set(id, r < 0.12 ? 0 : r < 0.45 ? between(0.25, 0.6) : between(0.7, 1.35));
    });
  }
  propensity.set(DEMO_IDS.participant, 1.1);
  persons.push(
    { id: 's-gs', nickname: 'Sandra (Freizeit)', role: 'staff', siteId: 'gs', leaderboardOptIn: false, notifications: true, joinedAt: historyStart.toISOString(), programEnd: addDays(now, 3650).toISOString(), surveysAnswered: [] },
    { id: 's-we', nickname: 'Henrik (Internatsdienst)', role: 'staff', siteId: 'we', leaderboardOptIn: false, notifications: true, joinedAt: historyStart.toISOString(), programEnd: addDays(now, 3650).toISOString(), surveysAnswered: [] },
    { id: 's-bp', nickname: 'Aylin (Freizeit)', role: 'staff', siteId: 'bp', leaderboardOptIn: false, notifications: true, joinedAt: historyStart.toISOString(), programEnd: addDays(now, 3650).toISOString(), surveysAnswered: [] },
    { id: DEMO_IDS.lead, nickname: 'Leitung Internat', role: 'lead', siteId: 'gs', leaderboardOptIn: false, notifications: true, joinedAt: historyStart.toISOString(), programEnd: addDays(now, 3650).toISOString(), surveysAnswered: [] },
  );
  const participants = persons.filter((p) => p.role === 'participant');
  const bySite = (siteId: string) => participants.filter((p) => p.siteId === siteId);

  // Saisons ----------------------------------------------------------------
  const seasonStart = addDays(thisWeek, -7 * 7);
  const seasons: Season[] = [
    {
      id: 'season-sommer',
      name: 'Sommer-Saison 2026',
      start: addDays(seasonStart, -7 * 12).toISOString(),
      end: seasonStart.toISOString(),
      status: 'archived',
      results: [
        { siteId: 'we', total: 6120, active: 23, perActive: 266.1 },
        { siteId: 'gs', total: 4980, active: 19, perActive: 262.1 },
        { siteId: 'bp', total: 3410, active: 14, perActive: 243.6 },
      ],
    },
    { id: 'season-herbst', name: 'Herbst-Saison 2026', start: seasonStart.toISOString(), end: addDays(seasonStart, 7 * 12).toISOString(), status: 'active' },
  ];

  // Events -----------------------------------------------------------------
  const at = (dayOffset: number, hour: number, minute = 0) =>
    new Date(now.getFullYear(), now.getMonth(), now.getDate() + dayOffset, hour, minute);
  const ev = (e: Omit<SportEvent, 'registered' | 'waitlist' | 'reminders'> & Partial<Pick<SportEvent, 'registered' | 'waitlist' | 'reminders'>>): SportEvent => ({
    registered: [],
    waitlist: [],
    reminders: [],
    ...e,
  });
  const ids = (siteId: string, from: number, count: number) => bySite(siteId).slice(from, from + count).map((p) => p.id);

  const runningStart = new Date(Math.floor((now.getTime() - 20 * MIN) / (5 * MIN)) * 5 * MIN);
  const events: SportEvent[] = [
    ev({
      id: 'ev-badminton',
      siteId: 'gs',
      title: 'Offener Badminton-Treff',
      kind: 'kurs',
      sport: 'Badminton',
      location: 'Sporthalle Goslar',
      start: runningStart.toISOString(),
      end: new Date(runningStart.getTime() + 2 * HOUR).toISOString(),
      capacity: 12,
      points: 15,
      description: 'Das neue Netz ist da! Einfach vorbeikommen und mitspielen – Schläger und Bälle liegen bereit.',
      registered: ids('gs', 3, 5),
    }),
    ev({
      id: 'ev-bouldern',
      siteId: 'gs',
      title: 'Schnuppertraining Bouldern',
      kind: 'schnupper',
      sport: 'Bouldern',
      location: 'Kletterhalle (Abfahrt am Haupteingang)',
      start: at(1, 17).toISOString(),
      end: at(1, 19).toISOString(),
      capacity: 8,
      points: 15,
      description: 'Mit dem örtlichen Kletterverein. Ohne Vorkenntnisse, Schuhe werden gestellt. Fahrt im Kleinbus.',
      registered: ids('gs', 1, 8).filter((id) => id !== DEMO_IDS.participant).slice(0, 8),
      waitlist: ids('gs', 10, 2),
    }),
    ev({
      id: 'ev-rueckenfit',
      siteId: 'gs',
      title: 'Rückenfit am Abend',
      kind: 'kurs',
      sport: 'Rückenfit',
      location: 'Fitnessraum Goslar',
      start: at(3, 18).toISOString(),
      end: at(3, 19).toISOString(),
      capacity: 10,
      points: 15,
      description: 'Sanfte Übungen für Rücken und Haltung. Für alle geeignet, jede Bewegung im eigenen Tempo.',
      registered: [DEMO_IDS.participant, ...ids('gs', 4, 4)],
      reminders: [DEMO_IDS.participant],
    }),
    ev({
      id: 'ev-volleyball',
      siteId: 'gs',
      title: 'Volleyball-Mixed-Turnier',
      kind: 'turnier',
      sport: 'Volleyball',
      location: 'Sporthalle Goslar',
      start: at(6, 14).toISOString(),
      end: at(6, 17).toISOString(),
      capacity: 24,
      points: 20,
      description: 'Teams werden vor Ort gemischt. Mitmachen zählt – Zuschauen und Anfeuern auch.',
      registered: ids('gs', 2, 9),
    }),
    ev({
      id: 'ev-fussballnacht',
      siteId: 'we',
      title: 'Fußball-Nacht',
      kind: 'themenabend',
      sport: 'Fußball',
      location: 'Sporthalle Weser-Ems',
      start: at(2, 19).toISOString(),
      end: at(2, 22).toISOString(),
      capacity: 20,
      points: 15,
      description: 'Hallenkick in gemischten Teams, danach gemeinsames Essen.',
      registered: ids('we', 0, 14),
    }),
    ev({
      id: 'ev-yoga',
      siteId: 'bp',
      title: 'Yoga für Einsteiger',
      kind: 'kurs',
      sport: 'Yoga',
      location: 'Sporthalle Bad Pyrmont',
      start: at(4, 17, 30).toISOString(),
      end: at(4, 18, 30).toISOString(),
      capacity: 12,
      points: 15,
      description: 'Ruhige Einheit für Anfängerinnen und Anfänger. Matten sind vorhanden.',
      registered: ids('bp', 0, 7),
    }),
  ];

  // Vergangene Events für Historie und Auswertung
  const pastTemplates: { siteId: string; title: string; kind: SportEvent['kind']; sport: string; weeksAgo: number; day: number; hour: number; capacity: number; points: number }[] = [
    { siteId: 'gs', title: 'Darts-Abend', kind: 'themenabend', sport: 'Darts', weeksAgo: 9, day: 2, hour: 19, capacity: 16, points: 15 },
    { siteId: 'gs', title: 'Schnuppertraining Boxen', kind: 'schnupper', sport: 'Boxen', weeksAgo: 5, day: 3, hour: 17, capacity: 10, points: 15 },
    { siteId: 'gs', title: 'Tischtennis-Herbstcup Gruppenphase', kind: 'turnier', sport: 'Tischtennis', weeksAgo: 2, day: 4, hour: 17, capacity: 16, points: 20 },
    { siteId: 'gs', title: 'Rückenfit am Abend', kind: 'kurs', sport: 'Rückenfit', weeksAgo: 1, day: 2, hour: 18, capacity: 10, points: 15 },
    { siteId: 'we', title: 'Volleyball-Abend', kind: 'themenabend', sport: 'Volleyball', weeksAgo: 7, day: 1, hour: 19, capacity: 20, points: 15 },
    { siteId: 'we', title: 'Darts-Sommercup', kind: 'turnier', sport: 'Darts', weeksAgo: 10, day: 4, hour: 18, capacity: 16, points: 20 },
    { siteId: 'we', title: 'Tischtennis-Herbstcup Gruppenphase', kind: 'turnier', sport: 'Tischtennis', weeksAgo: 2, day: 2, hour: 17, capacity: 16, points: 20 },
    { siteId: 'we', title: 'Fußball-Nacht', kind: 'themenabend', sport: 'Fußball', weeksAgo: 4, day: 4, hour: 19, capacity: 20, points: 15 },
    { siteId: 'bp', title: 'Yoga für Einsteiger', kind: 'kurs', sport: 'Yoga', weeksAgo: 3, day: 3, hour: 17, capacity: 12, points: 15 },
    { siteId: 'bp', title: 'Wanderung Bergkurpark', kind: 'themenabend', sport: 'Wandern', weeksAgo: 6, day: 5, hour: 10, capacity: 15, points: 15 },
    { siteId: 'bp', title: 'Tischtennis-Herbstcup Gruppenphase', kind: 'turnier', sport: 'Tischtennis', weeksAgo: 2, day: 3, hour: 17, capacity: 16, points: 20 },
    { siteId: 'bp', title: 'Schnuppertraining Rudern', kind: 'schnupper', sport: 'Rudern', weeksAgo: 8, day: 2, hour: 16, capacity: 8, points: 15 },
  ];
  for (const [i, t] of pastTemplates.entries()) {
    const start = new Date(addDays(thisWeek, -7 * t.weeksAgo + t.day).getTime() + t.hour * HOUR);
    if (start.getTime() < historyStart.getTime()) continue;
    const pool = bySite(t.siteId).filter((p) => (propensity.get(p.id) ?? 0) > 0.2);
    // Die Demo-Person war bisher nur beim Tischtennis-Cup – so kann sie in der Demo „Allrounder“ werden.
    const registered = pool
      .filter((p) => rnd() < 0.7 && (p.id !== DEMO_IDS.participant || t.sport === 'Tischtennis'))
      .slice(0, t.capacity)
      .map((p) => p.id);
    events.push(
      ev({
        id: `ev-past-${i}`,
        siteId: t.siteId,
        title: t.title,
        kind: t.kind,
        sport: t.sport,
        location: `Sporthalle ${sites.find((s) => s.id === t.siteId)!.name}`,
        start: start.toISOString(),
        end: new Date(start.getTime() + 2 * HOUR).toISOString(),
        capacity: t.capacity,
        points: t.points,
        description: '',
        registered,
      }),
    );
  }

  // Check-in-Historie --------------------------------------------------------
  const db: DB = {
    version: DB_VERSION,
    generatedAt: now.toISOString(),
    codeSecret: Math.floor(rnd() * 1e9).toString(36) + Math.floor(rnd() * 1e9).toString(36),
    sites,
    places,
    persons,
    checkins: [],
    events,
    challenges: [],
    seasons,
    tournaments: [],
    ideas: [],
    surveys: [],
    surveyResponses: [],
    announcements: [],
    notifications: [],
    settings: { weeklyGoal: 3, dailyPointCap: 40, deleteAfterDays: 30 },
  };

  type Candidate = { personId: string; at: Date; target: CheckinTarget; buddyOf?: boolean };
  const candidates: Candidate[] = [];
  // Ferienwoche/Feiertag und leichter Aufwärtstrend durch die Saison
  const weekFactor = (i: number) => [0.85, 0.9, 0.95, 1.0, 0.9, 1.0, 0.7, 1.05, 1.1, 1.0, 1.15, 1.1][i] ?? 1;

  for (let w = 0; w < HISTORY_WEEKS; w++) {
    const weekStart = addDays(historyStart, 7 * w);
    for (const p of participants) {
      if (p.id === DEMO_IDS.participant && w === HISTORY_WEEKS - 1) continue; // laufende Woche wird unten gesetzt
      const lambda = (propensity.get(p.id) ?? 0) * 2.6 * siteFactor[p.siteId] * weekFactor(w);
      let n = poisson(lambda);
      if (p.id === DEMO_IDS.participant) n = Math.max(2, Math.min(n, 4));
      for (let k = 0; k < n; k++) {
        const early = rnd() < 0.08 && p.id !== DEMO_IDS.participant;
        const hour = early ? between(6.3, 7.9) : rnd() < 0.5 ? between(15.5, 18) : between(18, 21);
        const when = new Date(weekStart.getTime() + Math.floor(between(0, 7)) * DAY + hour * HOUR);
        if (when.getTime() > now.getTime() - 30 * MIN || when.getTime() < Date.parse(p.joinedAt)) continue;
        const place = rnd() < 0.62 ? `${p.siteId}-gym` : `${p.siteId}-hall`;
        candidates.push({ personId: p.id, at: when, target: { type: 'place', placeId: place } });
        if (rnd() < 0.16) {
          const mate = pick(bySite(p.siteId).filter((m) => m.id !== p.id && (propensity.get(m.id) ?? 0) > 0));
          if (mate && mate.id !== DEMO_IDS.participant) {
            candidates.push({ personId: mate.id, at: new Date(when.getTime() + between(1, 8) * MIN), target: { type: 'place', placeId: place }, buddyOf: true });
          }
        }
      }
    }
  }
  // Event-Teilnahmen: ca. 85 % der Angemeldeten erscheinen
  for (const e of events) {
    if (Date.parse(e.end) > now.getTime()) continue;
    for (const pid of e.registered) {
      if (rnd() < 0.85) candidates.push({ personId: pid, at: new Date(Date.parse(e.start) + between(-10, 15) * MIN), target: { type: 'event', eventId: e.id } });
    }
  }
  // Demo-Person „Kalle“: zwei Aktivitäten in der laufenden Woche, damit der nächste Check-in das Wochenziel knackt.
  const weekday = (now.getDay() + 6) % 7;
  const kalleSlots =
    weekday >= 2
      ? [new Date(thisWeek.getTime() + 18 * HOUR), new Date(thisWeek.getTime() + DAY + 17.5 * HOUR)]
      : weekday === 1
        ? [new Date(thisWeek.getTime() + 18 * HOUR), new Date(Math.max(thisWeek.getTime() + DAY + 0.5 * HOUR, now.getTime() - 5 * HOUR))]
        : [new Date(Math.max(thisWeek.getTime(), now.getTime() - 10 * HOUR)), new Date(Math.max(thisWeek.getTime() + 10 * MIN, now.getTime() - 5 * HOUR))];
  for (const when of kalleSlots) {
    if (when.getTime() < now.getTime()) candidates.push({ personId: DEMO_IDS.participant, at: when, target: { type: 'place', placeId: 'gs-hall' } });
  }

  candidates.sort((a, b) => a.at.getTime() - b.at.getTime());
  let n = 0;
  for (const c of candidates) {
    const resolved = resolvedFor(db, c.target);
    if (!resolved) continue;
    const result = evaluateCheckin(db, c.personId, resolved, c.at);
    if (!result.ok) continue;
    db.checkins = applyCheckin(db.checkins, {
      id: `c-${(n++).toString(36)}`,
      personId: c.personId,
      resolved,
      evaluation: result.value,
      at: c.at,
      source: rnd() < 0.8 ? 'qr' : 'code',
    });
  }

  // Challenges ---------------------------------------------------------------
  const challenge = (c: Challenge) => c;
  db.challenges = [
    challenge({ id: 'ch-3x', scope: 'week', title: '3× Bewegung', description: 'Sei diese Woche dreimal aktiv – egal ob Fitnessraum, Halle oder Event.', metric: 'activities', target: 3, start: thisWeek.toISOString(), end: addDays(thisWeek, 7).toISOString(), icon: 'Activity', active: true }),
    challenge({ id: 'ch-neu', scope: 'week', title: 'Probier etwas Neues', description: 'Mach diese Woche bei einem Angebot mit, das du noch nicht kennst.', metric: 'newOffer', target: 1, start: thisWeek.toISOString(), end: addDays(thisWeek, 7).toISOString(), icon: 'Compass', active: true }),
    challenge({ id: 'ch-buddy', scope: 'week', title: 'Bring jemanden mit', description: 'Checkt zu zweit innerhalb von 10 Minuten am selben Ort ein – ihr bekommt beide einen Bonus.', metric: 'buddy', target: 1, start: thisWeek.toISOString(), end: addDays(thisWeek, 7).toISOString(), icon: 'HeartHandshake', active: true }),
    challenge({ id: 'ch-team150', scope: 'team', title: 'Gemeinsam stark', description: 'Schafft als Standort-Team zusammen die Check-ins in vier Wochen. Das Ziel richtet sich nach der Größe des Standorts.', metric: 'teamCheckins', target: 150, targetBySite: { gs: 150, we: 180, bp: 110 }, start: addDays(thisWeek, -14).toISOString(), end: addDays(thisWeek, 14).toISOString(), icon: 'Users', active: true }),
    challenge({ id: 'ch-events', scope: 'team', title: 'Event-Fieber', description: 'Sammelt als Team Event-Teilnahmen in dieser Saison.', metric: 'teamEvents', target: 40, targetBySite: { gs: 40, we: 48, bp: 30 }, start: seasonStart.toISOString(), end: addDays(seasonStart, 7 * 12).toISOString(), icon: 'CalendarHeart', active: true }),
    challenge({ id: 'ch-herbst', scope: 'season', title: 'Herbst-Challenge', description: 'Sei 6 Wochen lang jeweils mindestens zweimal pro Woche aktiv.', metric: 'activeWeeks', target: 6, start: addDays(thisWeek, -14).toISOString(), end: addDays(thisWeek, 7 * 4).toISOString(), icon: 'Leaf', active: true }),
    challenge({ id: 'ch-winter', scope: 'season', title: 'Winter-Challenge', description: 'Bleib auch in der dunklen Jahreszeit dran: 6 Wochen mit je zwei Aktivitäten.', metric: 'activeWeeks', target: 6, start: addDays(thisWeek, 7 * 4).toISOString(), end: addDays(thisWeek, 7 * 10).toISOString(), icon: 'Snowflake', active: true }),
  ];

  // Turniere -------------------------------------------------------------------
  const tp = (personId: string) => {
    const p = persons.find((x) => x.id === personId)!;
    return { id: `tp-${personId}`, name: p.nickname, personId, siteId: p.siteId };
  };
  const cupPlayers = ['p-gs-01', 'p-gs-03', 'p-gs-07', 'p-we-01', 'p-we-04', 'p-we-07', 'p-bp-02', 'p-bp-05'].map(tp);
  const groups = [
    { name: 'A', playerIds: [cupPlayers[0].id, cupPlayers[3].id, cupPlayers[6].id, cupPlayers[5].id] },
    { name: 'B', playerIds: [cupPlayers[1].id, cupPlayers[4].id, cupPlayers[7].id, cupPlayers[2].id] },
  ];
  const cupMatches = buildGroupStage(groups);
  const results: [number, number][] = [
    [3, 1], [2, 3], [3, 0], [1, 3], [3, 2], [3, 1],
    [0, 3], [3, 1], [3, 2], [2, 3],
  ];
  cupMatches.filter((m) => m.stage === 'group').forEach((m, i) => {
    if (results[i]) [m.scoreA, m.scoreB] = results[i];
  });
  const sommerPlayers = ['p-we-02', 'p-gs-04', 'p-bp-01', 'p-we-09'].map(tp);
  const sommerMatches = buildKnockout(sommerPlayers.map((p) => p.id));
  [[3, 1], [2, 3], [3, 2]].forEach(([a, b], i) => {
    sommerMatches[i].scoreA = a;
    sommerMatches[i].scoreB = b;
  });
  const tournaments: Tournament[] = [
    { id: 't-herbstcup', title: 'Tischtennis-Herbstcup', sport: 'Tischtennis', format: 'groups', status: 'running', scoreUnit: 'Sätze', createdAt: addDays(thisWeek, -16).toISOString(), players: cupPlayers, groups, matches: cupMatches },
    { id: 't-darts', title: 'Darts-Sommercup', sport: 'Darts', format: 'knockout', status: 'done', scoreUnit: 'Legs', createdAt: addDays(thisWeek, -70).toISOString(), players: sommerPlayers, groups: [], matches: sommerMatches },
  ];
  db.tournaments = tournaments;

  // Wünsch dir was --------------------------------------------------------------
  const voters = (count: number) => participants.filter(() => rnd() < count / participants.length).map((p) => p.id);
  const idea = (i: number, siteId: string, title: string, text: string, votes: number, status: Idea['status'] = 'neu'): Idea => ({
    id: `idea-${i}`,
    authorId: pick(bySite(siteId)).id,
    siteId,
    title,
    text,
    votes: voters(votes),
    status,
    createdAt: new Date(now.getTime() - between(2, 50) * DAY).toISOString(),
  });
  db.ideas = [
    idea(1, 'gs', 'Tischkicker im Aufenthaltsraum', 'Für die Abende, an denen man keine Lust auf Halle hat.', 21, 'umsetzung'),
    idea(2, 'we', 'Lauftreff am Sonntagmorgen', 'Lockere Runde, jedes Tempo willkommen. Gerne auch Walking.', 17),
    idea(3, 'bp', 'Schwimmbad-Ausflug einmal im Monat', 'Gemeinsam ins Hallenbad, Fahrt organisiert über das Internat.', 26, 'umsetzung'),
    idea(4, 'gs', 'Badminton-Netz für die Halle', 'Badminton geht auch ohne viel Erfahrung und macht Spaß.', 14, 'erledigt'),
    idea(5, 'we', 'Spieleabend mit Brettspielen', 'Nicht nur Sport – auch Gemeinschaft zählt.', 12),
    idea(6, 'bp', 'Entspannungskurs / Progressive Muskelentspannung', 'Hilft beim Abschalten nach einem langen Tag.', 19),
    idea(7, 'gs', 'Fahrrad-Werkstatt-Nachmittag', 'Räder gemeinsam fit machen, danach eine kleine Tour.', 9),
    idea(8, 'we', 'Musik im Fitnessraum per Bluetooth-Box', 'Mit leiser Hintergrundmusik trainiert es sich leichter.', 23),
    idea(9, 'bp', 'Boule-Bahn im Garten', 'Kann jede und jeder, auch mit Einschränkungen.', 11),
    idea(10, 'gs', 'Standortübergreifendes Fußballturnier', 'Einmal im Jahr alle drei Standorte an einem Ort.', 15),
  ];

  // Kurzumfrage -----------------------------------------------------------------
  const questions = [
    { id: 'q1', text: 'Wie zufrieden bist du mit dem Sport- und Freizeitangebot?' },
    { id: 'q2', text: 'Wie gut passen die Zeiten zu deinem Alltag?' },
    { id: 'q3', text: 'Wie wohl fühlst du dich bei den Angeboten?' },
  ];
  const q = Math.floor(now.getMonth() / 3) + 1;
  const prevQ = q === 1 ? 4 : q - 1;
  const prevYear = q === 1 ? now.getFullYear() - 1 : now.getFullYear();
  const surveys: Survey[] = [
    { id: 'survey-prev', title: `Kurzumfrage Q${prevQ} ${prevYear}`, quarter: `Q${prevQ} ${prevYear}`, questions, status: 'closed', start: addDays(now, -95).toISOString(), end: addDays(now, -70).toISOString() },
    { id: 'survey-now', title: `Kurzumfrage Q${q} ${now.getFullYear()}`, quarter: `Q${q} ${now.getFullYear()}`, questions, status: 'open', start: addDays(now, -3).toISOString(), end: addDays(now, 25).toISOString() },
  ];
  const comments = [
    'Mehr Angebote am Wochenende wären super.',
    'Die Betreuung in der Halle ist richtig gut.',
    'Fitnessraum ist abends oft voll.',
    'Ich traue mich jetzt auch zu Kursen – danke!',
    'Bitte mehr ruhige Angebote, nicht nur Ballsport.',
    'Die Ausflüge mit den Vereinen sind toll.',
  ];
  const responses: SurveyResponse[] = [];
  const answer = (base: number) => Math.max(1, Math.min(5, Math.round(base + between(-1.3, 1.3))));
  for (const [surveyId, count, shift] of [['survey-prev', 34, 0], ['survey-now', 9, 0.3]] as const) {
    for (let i = 0; i < count; i++) {
      const siteId = pick(sites).id;
      const c: Record<string, string> = {};
      if (rnd() < 0.3) c.q1 = pick(comments);
      responses.push({
        id: `sr-${surveyId}-${i}`,
        surveyId,
        siteId,
        answers: { q1: answer(3.9 + shift), q2: answer(3.3 + shift), q3: answer(4.2 + shift) },
        comments: c,
        at: new Date(Date.parse(surveys.find((s) => s.id === surveyId)!.start) + between(0, 3) * DAY).toISOString(),
      });
    }
  }
  db.surveys = surveys;
  db.surveyResponses = responses;
  // Antwort-Status (getrennt von den anonymen Antworten): viele haben die alte Umfrage beantwortet
  for (const p of participants) if (rnd() < 0.7) p.surveysAnswered.push('survey-prev');
  if (!persons.find((p) => p.id === DEMO_IDS.participant)!.surveysAnswered.includes('survey-prev')) {
    persons.find((p) => p.id === DEMO_IDS.participant)!.surveysAnswered.push('survey-prev');
  }

  // Ankündigungen & Benachrichtigungen ----------------------------------------------
  const announcements: Announcement[] = [
    { id: 'an-1', siteId: 'gs', author: 'Sandra (Freizeit)', text: 'Neu: Der Fitnessraum ist jetzt auch sonntags von 10 bis 14 Uhr geöffnet.', at: new Date(now.getTime() - 26 * HOUR).toISOString() },
    { id: 'an-2', siteId: 'gs', author: 'Sandra (Freizeit)', text: 'Das Badminton-Netz ist da – danke für eure Idee bei „Wünsch dir was“!', at: new Date(now.getTime() - 4 * DAY).toISOString() },
    { id: 'an-3', siteId: 'we', author: 'Henrik (Internatsdienst)', text: 'Fußball-Nacht: Bitte Hallenschuhe mitbringen.', at: new Date(now.getTime() - 2 * DAY).toISOString() },
    { id: 'an-4', siteId: 'bp', author: 'Aylin (Freizeit)', text: 'Yoga-Matten sind frisch gereinigt und liegen im Geräteraum.', at: new Date(now.getTime() - 3 * DAY).toISOString() },
  ];
  db.announcements = announcements;
  const notifications: AppNotification[] = [
    { id: 'n-1', personId: DEMO_IDS.participant, title: 'Erinnerung', text: '„Rückenfit am Abend“ findet bald statt. Du bist angemeldet.', at: new Date(now.getTime() - 2 * HOUR).toISOString(), read: false },
    { id: 'n-2', personId: DEMO_IDS.participant, title: 'Team Goslar', text: 'Euer Team hat diese Woche schon über 40 Check-ins. Stark!', at: new Date(now.getTime() - 20 * HOUR).toISOString(), read: true },
  ];
  db.notifications = notifications;

  return db;
}

export function resolvedFor(db: DB, target: CheckinTarget): ResolvedTarget | null {
  if (target.type === 'place') {
    const place = db.places.find((p) => p.id === target.placeId);
    if (!place) return null;
    return { target, siteId: place.siteId, offer: place.kind === 'gym' ? 'Fitnessraum' : 'Halle', label: place.name, basePoints: 10 };
  }
  const e = db.events.find((x) => x.id === target.eventId);
  if (!e) return null;
  return { target, siteId: e.siteId, offer: e.sport, label: e.title, basePoints: e.points };
}
