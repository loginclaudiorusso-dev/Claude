// Statische Klassen je Team (Tailwind erkennt nur vollständige Klassennamen).
import type { TeamKey } from '../domain/types';

export const TEAM_CLASSES: Record<TeamKey, { bg: string; text: string; border: string; soft: string; fill: string; stroke: string }> = {
  gs: { bg: 'bg-team-gs', text: 'text-team-gs', border: 'border-team-gs', soft: 'bg-team-gs/15', fill: 'fill-team-gs', stroke: 'stroke-team-gs' },
  we: { bg: 'bg-team-we', text: 'text-team-we', border: 'border-team-we', soft: 'bg-team-we/15', fill: 'fill-team-we', stroke: 'stroke-team-we' },
  bp: { bg: 'bg-team-bp', text: 'text-team-bp', border: 'border-team-bp', soft: 'bg-team-bp/15', fill: 'fill-team-bp', stroke: 'stroke-team-bp' },
};

export const TEAM_VAR: Record<TeamKey, string> = { gs: 'var(--team-gs)', we: 'var(--team-we)', bp: 'var(--team-bp)' };
