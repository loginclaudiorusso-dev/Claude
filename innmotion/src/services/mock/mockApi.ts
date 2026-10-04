import { earnedBadges, newlyEarned } from '../../domain/badges';
import { activitiesInWeek, applyCheckin, evaluateCheckin, resolveCode } from '../../domain/checkin';
import { activeSeason, siteStandings } from '../../domain/league';
import { addDays, fmt, startOfWeek } from '../../domain/time';
import { buildGroupStage, buildKnockout, splitGroups } from '../../domain/tournament';
import type { DB, Season, SportEvent, Tournament } from '../../domain/types';
import { resolvedFor } from '../../seed/generate';
import type { CheckinResponse, InnmotionApi } from '../api';
import { useDbStore } from './store';

let seq = 0;
export const uid = (prefix: string) => `${prefix}-${Date.now().toString(36)}${(seq++).toString(36)}${Math.random().toString(36).slice(2, 6)}`;

const get = () => useDbStore.getState().db;
const set = (fn: (db: DB) => DB) => useDbStore.getState().setDb(fn);
const done = <T,>(v: T) => Promise.resolve(v);

function notify(db: DB, personIds: string[], title: string, text: string): DB {
  const now = new Date().toISOString();
  const targets = db.persons.filter((p) => personIds.includes(p.id) && p.notifications);
  return {
    ...db,
    notifications: [...targets.map((p) => ({ id: uid('n'), personId: p.id, title, text, at: now, read: false })), ...db.notifications],
  };
}

function doCheckin(personId: string, raw: string | null, source: 'qr' | 'code' | 'staff', targetId?: string): CheckinResponse {
  const db = get();
  const now = new Date();
  let resolved;
  if (raw !== null) {
    const r = resolveCode(db, personId, raw, now);
    if (!r.ok) return r;
    resolved = r.value;
  } else {
    const place = db.places.find((p) => p.id === targetId);
    resolved = resolvedFor(db, place ? { type: 'place', placeId: targetId! } : { type: 'event', eventId: targetId! });
    if (!resolved) return { ok: false, reason: 'Ort oder Event nicht gefunden.' };
  }
  const evaluation = evaluateCheckin(db, personId, resolved, now);
  if (!evaluation.ok) return evaluation;
  const before = earnedBadges(db, personId, now);
  const next: DB = { ...db, checkins: applyCheckin(db.checkins, { id: uid('c'), personId, resolved, evaluation: evaluation.value, at: now, source }) };
  const after = earnedBadges(next, personId, new Date(now.getTime() + 1));
  useDbStore.getState().setDb(() => next);
  const buddy = evaluation.value.buddy ? db.persons.find((p) => p.id === evaluation.value.buddy!.personId) : undefined;
  return {
    ok: true,
    label: resolved.label,
    offer: resolved.offer,
    points: evaluation.value.points,
    breakdown: evaluation.value.breakdown,
    newBadges: newlyEarned(before, after),
    buddyName: buddy?.nickname,
    weeklyGoalReached: evaluation.value.weeklyGoalReached,
    weekCount: activitiesInWeek(next.checkins, personId, now),
  };
}

export const mockApi: InnmotionApi = {
  // ---------------------------------------------------------------- Teilnehmende
  checkIn: (personId, raw, source) => done(doCheckin(personId, raw, source)),

  toggleRegistration(personId, eventId) {
    const db = get();
    const ev = db.events.find((e) => e.id === eventId);
    if (!ev) return done({ status: 'unregistered' as const, message: 'Event nicht gefunden.' });
    if (ev.registered.includes(personId)) {
      // Abmelden → erste Person der Warteliste rückt nach
      const [promoted, ...rest] = ev.waitlist;
      let next: DB = {
        ...db,
        events: db.events.map((e) =>
          e.id === eventId ? { ...e, registered: [...e.registered.filter((id) => id !== personId), ...(promoted ? [promoted] : [])], waitlist: rest } : e,
        ),
      };
      if (promoted) next = notify(next, [promoted], 'Du bist nachgerückt', `Für „${ev.title}“ ist ein Platz frei geworden. Du bist jetzt angemeldet.`);
      set(() => next);
      return done({ status: 'unregistered' as const, message: 'Du bist abgemeldet. Danke, dass du Bescheid gibst!' });
    }
    if (ev.waitlist.includes(personId)) {
      set((d) => ({ ...d, events: d.events.map((e) => (e.id === eventId ? { ...e, waitlist: e.waitlist.filter((id) => id !== personId) } : e)) }));
      return done({ status: 'unregistered' as const, message: 'Du stehst nicht mehr auf der Warteliste.' });
    }
    if (ev.registered.length >= ev.capacity) {
      set((d) => ({ ...d, events: d.events.map((e) => (e.id === eventId ? { ...e, waitlist: [...e.waitlist, personId] } : e)) }));
      return done({ status: 'waitlist' as const, message: `Alle Plätze sind belegt. Du bist auf Platz ${ev.waitlist.length + 1} der Warteliste.` });
    }
    set((d) => ({ ...d, events: d.events.map((e) => (e.id === eventId ? { ...e, registered: [...e.registered, personId], reminders: [...new Set([...e.reminders, personId])] } : e)) }));
    return done({ status: 'registered' as const, message: `Du bist angemeldet. Wir erinnern dich vorher.` });
  },

  toggleReminder(personId, eventId) {
    let on = false;
    set((d) => ({
      ...d,
      events: d.events.map((e) => {
        if (e.id !== eventId) return e;
        on = !e.reminders.includes(personId);
        return { ...e, reminders: on ? [...e.reminders, personId] : e.reminders.filter((id) => id !== personId) };
      }),
    }));
    if (on) {
      const ev = get().events.find((e) => e.id === eventId)!;
      // Simulierte Web-Push-Erinnerung
      set((d) => notify(d, [personId], 'Erinnerung aktiviert', `Wir erinnern dich an „${ev.title}“ (${fmt.dateTime(ev.start)}).`));
    }
    return done(on);
  },

  updateProfile(personId, patch) {
    set((d) => ({ ...d, persons: d.persons.map((p) => (p.id === personId ? { ...p, ...patch } : p)) }));
    return done(undefined);
  },

  deleteAccount(personId) {
    // Konto und alle personenbezogenen Einträge entfernen. Anonyme Umfrage-Antworten bleiben (nicht zuordenbar).
    set((d) => ({
      ...d,
      persons: d.persons.filter((p) => p.id !== personId),
      checkins: d.checkins.filter((c) => c.personId !== personId).map((c) => (c.buddyId === personId ? { ...c, buddyId: undefined } : c)),
      events: d.events.map((e) => ({
        ...e,
        registered: e.registered.filter((id) => id !== personId),
        waitlist: e.waitlist.filter((id) => id !== personId),
        reminders: e.reminders.filter((id) => id !== personId),
      })),
      ideas: d.ideas.map((i) => ({ ...i, votes: i.votes.filter((v) => v !== personId), authorId: i.authorId === personId ? 'gelöscht' : i.authorId })),
      notifications: d.notifications.filter((n) => n.personId !== personId),
      tournaments: d.tournaments.map((t) => ({ ...t, players: t.players.map((p) => (p.personId === personId ? { ...p, personId: undefined, name: 'Gelöschtes Konto' } : p)) })),
    }));
    return done(undefined);
  },

  submitIdea(personId, title, text) {
    const person = get().persons.find((p) => p.id === personId)!;
    set((d) => ({
      ...d,
      ideas: [{ id: uid('idea'), authorId: personId, siteId: person.siteId, title, text, votes: [personId], status: 'neu', createdAt: new Date().toISOString() }, ...d.ideas],
    }));
    return done(undefined);
  },

  toggleVote(personId, ideaId) {
    set((d) => ({
      ...d,
      ideas: d.ideas.map((i) => (i.id === ideaId ? { ...i, votes: i.votes.includes(personId) ? i.votes.filter((v) => v !== personId) : [...i.votes, personId] } : i)),
    }));
    return done(undefined);
  },

  submitSurvey(personId, surveyId, answers, comments) {
    const person = get().persons.find((p) => p.id === personId)!;
    set((d) => ({
      ...d,
      // Antwort ohne Personenbezug speichern; getrennt nur vermerken, dass die Person teilgenommen hat.
      surveyResponses: [...d.surveyResponses, { id: uid('sr'), surveyId, siteId: person.siteId, answers, comments, at: new Date().toISOString() }],
      persons: d.persons.map((p) => (p.id === personId ? { ...p, surveysAnswered: [...p.surveysAnswered, surveyId] } : p)),
    }));
    return done(undefined);
  },

  markNotificationsRead(personId) {
    set((d) => ({ ...d, notifications: d.notifications.map((n) => (n.personId === personId ? { ...n, read: true } : n)) }));
    return done(undefined);
  },

  // ---------------------------------------------------------------- Betreuung
  removeCheckin(checkinId) {
    set((d) => ({ ...d, checkins: d.checkins.filter((c) => c.id !== checkinId) }));
    return done(undefined);
  },

  adjustCheckinPoints(checkinId, points) {
    set((d) => ({
      ...d,
      checkins: d.checkins.map((c) =>
        c.id === checkinId ? { ...c, points, breakdown: [...c.breakdown, { label: 'Korrektur durch Betreuung', points: points - c.points }] } : c,
      ),
    }));
    return done(undefined);
  },

  addManualCheckin: (personId, targetId) => done(doCheckin(personId, null, 'staff', targetId)),

  createEvent(input) {
    const ev: SportEvent = { ...input, id: uid('ev'), registered: [], waitlist: [], reminders: [] };
    set((d) => {
      const withEvent = { ...d, events: [...d.events, ev] };
      const ids = d.persons.filter((p) => p.role === 'participant' && p.siteId === input.siteId).map((p) => p.id);
      return notify(withEvent, ids, 'Neues Event', `${input.title} · ${fmt.dateTime(input.start)}`);
    });
    return done(ev);
  },

  sendAnnouncement(siteId, author, text) {
    const recipients = get().persons.filter((p) => p.role === 'participant' && p.siteId === siteId);
    set((d) =>
      notify(
        { ...d, announcements: [{ id: uid('an'), siteId, author, text, at: new Date().toISOString() }, ...d.announcements] },
        recipients.map((p) => p.id),
        'Ankündigung',
        text,
      ),
    );
    return done(recipients.filter((p) => p.notifications).length);
  },

  setIdeaStatus(ideaId, status) {
    const idea = get().ideas.find((i) => i.id === ideaId);
    set((d) => {
      const next = { ...d, ideas: d.ideas.map((i) => (i.id === ideaId ? { ...i, status } : i)) };
      return idea && status === 'umsetzung' ? notify(next, idea.votes, 'Deine Idee wird umgesetzt', `„${idea.title}“ wird umgesetzt. Danke fürs Mitmachen!`) : next;
    });
    return done(undefined);
  },

  createTournament(input) {
    const players = input.players.map((p) => ({ ...p, id: uid('tp') }));
    const ids = players.map((p) => p.id);
    const groups = input.format === 'groups' ? splitGroups(ids, Math.max(1, Math.min(input.groupCount, Math.floor(ids.length / 2)))) : [];
    const t: Tournament = {
      id: uid('t'),
      title: input.title,
      sport: input.sport,
      format: input.format,
      status: 'running',
      scoreUnit: input.scoreUnit,
      createdAt: new Date().toISOString(),
      players,
      groups,
      matches: input.format === 'groups' ? buildGroupStage(groups) : buildKnockout(ids),
    };
    set((d) => ({ ...d, tournaments: [t, ...d.tournaments] }));
    return done(t);
  },

  recordResult(tournamentId, matchId, scoreA, scoreB) {
    set((d) => ({
      ...d,
      tournaments: d.tournaments.map((t) => (t.id === tournamentId ? { ...t, matches: t.matches.map((m) => (m.id === matchId ? { ...m, scoreA, scoreB } : m)) } : t)),
    }));
    return done(undefined);
  },

  finishTournament(tournamentId) {
    set((d) => ({ ...d, tournaments: d.tournaments.map((t) => (t.id === tournamentId ? { ...t, status: 'done' } : t)) }));
    return done(undefined);
  },

  // ---------------------------------------------------------------- Leitung
  updateSite(siteId, patch) {
    set((d) => ({ ...d, sites: d.sites.map((s) => (s.id === siteId ? { ...s, ...patch } : s)) }));
    return done(undefined);
  },

  addPlace(siteId, name, kind) {
    set((d) => ({ ...d, places: [...d.places, { id: uid('pl'), siteId, name, kind, active: true }] }));
    return done(undefined);
  },

  togglePlace(placeId) {
    set((d) => ({ ...d, places: d.places.map((p) => (p.id === placeId ? { ...p, active: !p.active } : p)) }));
    return done(undefined);
  },

  saveChallenge(challenge) {
    set((d) => ({
      ...d,
      challenges: d.challenges.some((c) => c.id === challenge.id) ? d.challenges.map((c) => (c.id === challenge.id ? challenge : c)) : [...d.challenges, challenge],
    }));
    return done(undefined);
  },

  toggleChallenge(challengeId) {
    set((d) => ({ ...d, challenges: d.challenges.map((c) => (c.id === challengeId ? { ...c, active: !c.active } : c)) }));
    return done(undefined);
  },

  endSeason() {
    const db = get();
    const season = activeSeason(db);
    if (!season) return done(undefined);
    const now = new Date();
    const results = siteStandings(db, new Date(season.start), now).map(({ siteId, total, active, perActive }) => ({ siteId, total, active, perActive }));
    const archived: Season = { ...season, status: 'archived', end: now.toISOString(), results };
    set((d) => ({ ...d, seasons: d.seasons.map((s) => (s.id === season.id ? archived : s)) }));
    return done(archived);
  },

  startSeason(name, weeks) {
    // Neue Saison = Punkte starten bei null (Wertung zählt ab Saisonbeginn). Historie bleibt fürs Dashboard erhalten.
    const start = new Date();
    const season: Season = { id: uid('season'), name, start: start.toISOString(), end: addDays(startOfWeek(start), weeks * 7).toISOString(), status: 'active' };
    set((d) => ({ ...d, seasons: [...d.seasons.map((s) => (s.status === 'active' ? { ...s, status: 'archived' as const } : s)), season] }));
    return done(season);
  },

  updateSettings(patch) {
    set((d) => ({ ...d, settings: { ...d.settings, ...patch } }));
    return done(undefined);
  },

  resetDemo() {
    useDbStore.getState().reset();
    return done(undefined);
  },
};

export const api: InnmotionApi = mockApi;
