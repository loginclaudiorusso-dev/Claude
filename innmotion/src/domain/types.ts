// Datenmodell von INNmotion. Bewusst datensparsam: Spitznamen statt Klarnamen,
// keine Gesundheits-, Körper- oder Standortdaten.

export type Role = 'participant' | 'staff' | 'lead';
export type TeamKey = 'gs' | 'we' | 'bp';

export interface Site {
  id: string;
  name: string;
  short: string;
  team: TeamKey;
  teamName: string;
  /** Belegung (Plätze im Internat) – von der Leitung manuell gepflegt, Basis der Teilnahmequote. */
  occupancy: number;
}

export type PlaceKind = 'gym' | 'hall';

export interface Place {
  id: string;
  siteId: string;
  name: string;
  kind: PlaceKind;
  active: boolean;
}

export interface Person {
  id: string;
  nickname: string;
  role: Role;
  siteId: string;
  /** Optionale Untergruppe, z. B. „Haus A · 1. OG“. */
  subgroup?: string;
  leaderboardOptIn: boolean;
  notifications: boolean;
  joinedAt: string;
  /** Voraussichtliches Maßnahmeende – Grundlage für die automatische Löschung. */
  programEnd: string;
  /** IDs bereits beantworteter Umfragen. Die Antworten selbst sind davon getrennt und anonym. */
  surveysAnswered: string[];
}

export interface PointItem {
  label: string;
  points: number;
}

export type CheckinTarget = { type: 'place'; placeId: string } | { type: 'event'; eventId: string };

export interface Checkin {
  id: string;
  personId: string;
  siteId: string;
  at: string;
  target: CheckinTarget;
  /** Angebot, z. B. „Fitnessraum“, „Halle“, „Yoga“ – für Allrounder-Abzeichen und Auswertung. */
  offer: string;
  points: number;
  breakdown: PointItem[];
  buddyId?: string;
  source: 'qr' | 'code' | 'staff';
}

export type EventKind = 'turnier' | 'themenabend' | 'schnupper' | 'kurs';

export interface SportEvent {
  id: string;
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
  registered: string[];
  waitlist: string[];
  reminders: string[];
}

export type ChallengeScope = 'week' | 'team' | 'season';
export type ChallengeMetric =
  | 'activities'
  | 'newOffer'
  | 'buddy'
  | 'teamCheckins'
  | 'teamEvents'
  | 'activeWeeks';

export interface Challenge {
  id: string;
  scope: ChallengeScope;
  title: string;
  description: string;
  metric: ChallengeMetric;
  target: number;
  /** Team-Challenges: Ziel je Standort (fair nach Größe). */
  targetBySite?: Record<string, number>;
  start: string;
  end: string;
  icon: string;
  active: boolean;
}

export interface SeasonResult {
  siteId: string;
  total: number;
  active: number;
  perActive: number;
}

export interface Season {
  id: string;
  name: string;
  start: string;
  end: string;
  status: 'active' | 'archived';
  results?: SeasonResult[];
}

export type Slot =
  | { kind: 'player'; id: string }
  | { kind: 'group'; group: string; rank: number }
  | { kind: 'winner'; match: string }
  | { kind: 'bye' };

export interface Match {
  id: string;
  stage: 'group' | 'ko';
  group?: string;
  round?: number;
  label?: string;
  a: Slot;
  b: Slot;
  scoreA?: number;
  scoreB?: number;
}

export interface TournamentPlayer {
  id: string;
  name: string;
  personId?: string;
  siteId: string;
}

export interface Tournament {
  id: string;
  title: string;
  sport: string;
  format: 'groups' | 'knockout';
  status: 'running' | 'done';
  scoreUnit: string;
  createdAt: string;
  players: TournamentPlayer[];
  groups: { name: string; playerIds: string[] }[];
  matches: Match[];
}

export type IdeaStatus = 'neu' | 'umsetzung' | 'erledigt';

export interface Idea {
  id: string;
  authorId: string;
  siteId: string;
  title: string;
  text: string;
  votes: string[];
  status: IdeaStatus;
  createdAt: string;
}

export interface Survey {
  id: string;
  title: string;
  quarter: string;
  questions: { id: string; text: string }[];
  status: 'open' | 'closed';
  start: string;
  end: string;
}

/** Anonym: keine Personen-ID, nur Standort für die aggregierte Auswertung. */
export interface SurveyResponse {
  id: string;
  surveyId: string;
  siteId: string;
  answers: Record<string, number>;
  comments: Record<string, string>;
  at: string;
}

export interface Announcement {
  id: string;
  siteId: string;
  author: string;
  text: string;
  at: string;
}

export interface AppNotification {
  id: string;
  personId: string;
  title: string;
  text: string;
  at: string;
  read: boolean;
}

export interface Settings {
  weeklyGoal: number;
  dailyPointCap: number;
  /** Konten werden X Tage nach Maßnahmeende automatisch gelöscht. */
  deleteAfterDays: number;
}

export interface DB {
  version: number;
  generatedAt: string;
  codeSecret: string;
  sites: Site[];
  places: Place[];
  persons: Person[];
  checkins: Checkin[];
  events: SportEvent[];
  challenges: Challenge[];
  seasons: Season[];
  tournaments: Tournament[];
  ideas: Idea[];
  surveys: Survey[];
  surveyResponses: SurveyResponse[];
  announcements: Announcement[];
  notifications: AppNotification[];
  settings: Settings;
}
