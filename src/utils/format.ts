/** Display formatting (German locale conventions), pure and testable. */
import type { DayKey, RecoveryZone, StrainLevel } from '@/types/health';

const WEEKDAYS_SHORT = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
const MONTHS_SHORT = [
  'Jan',
  'Feb',
  'Mär',
  'Apr',
  'Mai',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Okt',
  'Nov',
  'Dez',
];

function parts(day: DayKey) {
  const [y, m, d] = day.split('-').map(Number);
  return new Date(y!, m! - 1, d!);
}

/** 1234.5 → "1.234,5" */
export function formatNumber(value: number, decimals = 0): string {
  const fixed = Math.abs(value).toFixed(decimals);
  const [int, frac] = fixed.split('.');
  const grouped = int!.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${value < 0 ? '−' : ''}${grouped}${frac ? `,${frac}` : ''}`;
}

/** 452 → "7 h 32 min" */
export function formatDuration(minutes: number): string {
  const m = Math.max(0, Math.round(minutes));
  const h = Math.floor(m / 60);
  const rest = m % 60;
  if (h === 0) return `${rest} min`;
  return rest === 0 ? `${h} h` : `${h} h ${rest} min`;
}

/** Signed value: +3,2 / −12 */
export function formatSigned(value: number, decimals = 0): string {
  if (Math.abs(value) < 10 ** -decimals / 2) return formatNumber(0, decimals);
  return `${value > 0 ? '+' : ''}${formatNumber(value, decimals)}`;
}

export function formatWeekday(day: DayKey): string {
  return WEEKDAYS_SHORT[parts(day).getDay()]!;
}

/** "20. Sep" */
export function formatShortDate(day: DayKey): string {
  const d = parts(day);
  return `${d.getDate()}. ${MONTHS_SHORT[d.getMonth()]}`;
}

/** "Sonntag, 20. September" style header without Intl (Hermes-safe). */
export function formatLongDate(day: DayKey): string {
  const long = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
  const months = [
    'Januar',
    'Februar',
    'März',
    'April',
    'Mai',
    'Juni',
    'Juli',
    'August',
    'September',
    'Oktober',
    'November',
    'Dezember',
  ];
  const d = parts(day);
  return `${long[d.getDay()]}, ${d.getDate()}. ${months[d.getMonth()]}`;
}

export function formatClock(timestamp: number): string {
  const d = new Date(timestamp);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export const ZONE_LABEL: Record<RecoveryZone, string> = {
  green: 'Bereit',
  yellow: 'Moderat',
  red: 'Erholung nötig',
};

export const STRAIN_LABEL: Record<StrainLevel, string> = {
  light: 'Leicht',
  moderate: 'Moderat',
  high: 'Hoch',
  allOut: 'Maximal',
};
