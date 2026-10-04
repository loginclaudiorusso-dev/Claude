// Zeit-Hilfen (lokale Zeit, Woche beginnt am Montag).

export const MIN = 60_000;
export const HOUR = 60 * MIN;
export const DAY = 24 * HOUR;

export function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

export function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export function startOfWeek(d: Date): Date {
  const day = startOfDay(d);
  const offset = (day.getDay() + 6) % 7; // Montag = 0
  return addDays(day, -offset);
}

export function dayKey(d: Date | string): string {
  const x = typeof d === 'string' ? new Date(d) : d;
  const m = String(x.getMonth() + 1).padStart(2, '0');
  const day = String(x.getDate()).padStart(2, '0');
  return `${x.getFullYear()}-${m}-${day}`;
}

export function inRange(at: string | Date, from: Date, to: Date): boolean {
  const t = typeof at === 'string' ? Date.parse(at) : at.getTime();
  return t >= from.getTime() && t < to.getTime();
}

/** ISO-Kalenderwoche. */
export function isoWeek(d: Date): number {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const dayNum = (t.getUTCDay() + 6) % 7;
  t.setUTCDate(t.getUTCDate() - dayNum + 3);
  const firstThursday = new Date(Date.UTC(t.getUTCFullYear(), 0, 4));
  return 1 + Math.round(((t.getTime() - firstThursday.getTime()) / DAY - 3 + ((firstThursday.getUTCDay() + 6) % 7)) / 7);
}

/** Liste der Wochenanfänge, älteste zuerst, inkl. der Woche von `until`. */
export function weekStarts(count: number, until: Date): Date[] {
  const last = startOfWeek(until);
  return Array.from({ length: count }, (_, i) => addDays(last, -7 * (count - 1 - i)));
}

const weekdayFmt = new Intl.DateTimeFormat('de-DE', { weekday: 'short' });
const dateFmt = new Intl.DateTimeFormat('de-DE', { day: 'numeric', month: 'short' });
const timeFmt = new Intl.DateTimeFormat('de-DE', { hour: '2-digit', minute: '2-digit' });

export const fmt = {
  time: (d: string | Date | number) => timeFmt.format(new Date(d)),
  date: (d: string | Date) => dateFmt.format(new Date(d)),
  weekday: (d: string | Date) => weekdayFmt.format(new Date(d)).replace('.', ''),
  dateTime: (d: string | Date) => `${weekdayFmt.format(new Date(d)).replace('.', '')}, ${dateFmt.format(new Date(d))} · ${timeFmt.format(new Date(d))}`,
  relativeDay(d: string | Date, now = new Date()): string {
    const diff = Math.round((startOfDay(new Date(d)).getTime() - startOfDay(now).getTime()) / DAY);
    if (diff === 0) return 'Heute';
    if (diff === 1) return 'Morgen';
    if (diff === -1) return 'Gestern';
    return `${weekdayFmt.format(new Date(d)).replace('.', '')}, ${dateFmt.format(new Date(d))}`;
  },
  week: (d: Date) => `KW ${isoWeek(d)}`,
};
