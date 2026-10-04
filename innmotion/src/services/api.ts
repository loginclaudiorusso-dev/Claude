// Service-Schnittstelle. Die UI kennt nur diese Signaturen.
// Im Prototyp implementiert `mock/mockApi.ts` sie über einen lokalen Store (Zustand + localStorage).
// Für den echten Betrieb wird eine zweite Implementierung (z. B. Supabase mit EU-Hosting)
// geschrieben, die dieselbe Schnittstelle erfüllt – Screens bleiben unverändert.

import type { BadgeDef } from '../domain/badges';
import type { Challenge, EventKind, IdeaStatus, Person, PointItem, Season, Settings, Site, SportEvent, Tournament } from '../domain/types';

export interface CheckinSuccess {
  ok: true;
  label: string;
  offer: string;
  points: number;
  breakdown: PointItem[];
  newBadges: BadgeDef[];
  buddyName?: string;
  weeklyGoalReached: boolean;
  weekCount: number;
}
export type CheckinResponse = CheckinSuccess | { ok: false; reason: string };

export type RegisterResponse = { status: 'registered' | 'waitlist' | 'unregistered' | 'promoted'; message: string };

export interface NewEventInput {
  siteId: string;
  title: string;
  kind: EventKind;
  sport: string;
  location: string;
  start: string;
  end: string;
  capacity: number;
  points: number;
  description: string;
}

export interface NewTournamentInput {
  title: string;
  sport: string;
  format: Tournament['format'];
  scoreUnit: string;
  players: { name: string; personId?: string; siteId: string }[];
  groupCount: number;
}

export interface InnmotionApi {
  // Teilnehmende
  checkIn(personId: string, rawCode: string, source: 'qr' | 'code'): Promise<CheckinResponse>;
  toggleRegistration(personId: string, eventId: string): Promise<RegisterResponse>;
  toggleReminder(personId: string, eventId: string): Promise<boolean>;
  updateProfile(personId: string, patch: Partial<Pick<Person, 'nickname' | 'subgroup' | 'leaderboardOptIn' | 'notifications'>>): Promise<void>;
  deleteAccount(personId: string): Promise<void>;
  submitIdea(personId: string, title: string, text: string): Promise<void>;
  toggleVote(personId: string, ideaId: string): Promise<void>;
  submitSurvey(personId: string, surveyId: string, answers: Record<string, number>, comments: Record<string, string>): Promise<void>;
  markNotificationsRead(personId: string): Promise<void>;

  // Betreuung
  removeCheckin(checkinId: string): Promise<void>;
  adjustCheckinPoints(checkinId: string, points: number): Promise<void>;
  addManualCheckin(personId: string, placeOrEventId: string): Promise<CheckinResponse>;
  createEvent(input: NewEventInput): Promise<SportEvent>;
  sendAnnouncement(siteId: string, author: string, text: string): Promise<number>;
  setIdeaStatus(ideaId: string, status: IdeaStatus): Promise<void>;
  createTournament(input: NewTournamentInput): Promise<Tournament>;
  recordResult(tournamentId: string, matchId: string, scoreA: number | undefined, scoreB: number | undefined): Promise<void>;
  finishTournament(tournamentId: string): Promise<void>;

  // Leitung
  updateSite(siteId: string, patch: Partial<Pick<Site, 'occupancy' | 'name'>>): Promise<void>;
  addPlace(siteId: string, name: string, kind: 'gym' | 'hall'): Promise<void>;
  togglePlace(placeId: string): Promise<void>;
  saveChallenge(challenge: Challenge): Promise<void>;
  toggleChallenge(challengeId: string): Promise<void>;
  endSeason(): Promise<Season | undefined>;
  startSeason(name: string, weeks: number): Promise<Season>;
  updateSettings(patch: Partial<Settings>): Promise<void>;

  // Demo
  resetDemo(): Promise<void>;
}
