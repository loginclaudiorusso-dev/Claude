import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Bell, BellOff, CalendarDays, Clock, MapPin, QrCode, Ticket, Users, Zap } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { addDays, fmt, startOfDay, startOfWeek } from '../../domain/time';
import type { EventKind, SportEvent } from '../../domain/types';
import { Button, Card, Chip, EmptyState, IconButton, LargeTitle, Page, ProgressBar, Segmented, cx, useToast } from '../../components/ui';

export const KIND_LABEL: Record<EventKind, string> = {
  turnier: 'Turnier',
  themenabend: 'Themenabend',
  schnupper: 'Schnuppertraining',
  kurs: 'Kurs',
};

export function registrationLabel(ev: SportEvent, personId: string): { state: 'registered' | 'waitlist' | 'none'; action: string; text: string } {
  if (ev.registered.includes(personId)) return { state: 'registered', action: 'Abmelden', text: 'Du bist angemeldet' };
  const pos = ev.waitlist.indexOf(personId);
  if (pos >= 0) return { state: 'waitlist', action: 'Warteliste verlassen', text: `Warteliste · Platz ${pos + 1}` };
  return { state: 'none', action: ev.registered.length >= ev.capacity ? 'Auf Warteliste' : 'Anmelden', text: '' };
}

export function EventDateTile({ start, compact }: { start: string; compact?: boolean }) {
  const d = new Date(start);
  return (
    <div className={cx('flex shrink-0 flex-col items-center justify-center rounded-[16px] bg-accent-soft text-accent', compact ? 'size-12' : 'size-14')} aria-hidden>
      <span className="text-[11px] font-bold uppercase">{fmt.weekday(d)}</span>
      <span className="tnum text-[22px] font-extrabold leading-none">{d.getDate()}</span>
    </div>
  );
}

export function Events() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const [view, setView] = useState<'list' | 'week'>('list');
  const [weekOffset, setWeekOffset] = useState(0);

  const upcoming = useMemo(
    () => db.events.filter((e) => e.siteId === me.siteId && Date.parse(e.end) > now.getTime()).sort((a, b) => Date.parse(a.start) - Date.parse(b.start)),
    [db.events, me.siteId, now],
  );
  const mine = upcoming.filter((e) => e.registered.includes(me.id) || e.waitlist.includes(me.id));

  return (
    <Page>
      <LargeTitle title="Events" subtitle="Turniere, Themenabende, Schnuppertrainings und Kurse an deinem Standort." />
      <Segmented
        label="Ansicht"
        value={view}
        onChange={setView}
        options={[
          { value: 'list', label: 'Liste' },
          { value: 'week', label: 'Woche' },
        ]}
      />
      {view === 'list' ? (
        <div className="mt-5 space-y-3">
          {mine.length > 0 && (
            <p className="text-[14px] font-semibold text-ink-2">
              <Ticket className="mr-1 inline size-4 align-[-3px]" aria-hidden /> Du bist bei {mine.length} {mine.length === 1 ? 'Event' : 'Events'} dabei.
            </p>
          )}
          {upcoming.length === 0 && <EmptyState icon={<CalendarDays />} title="Gerade keine Events" text="Schau bald wieder rein – oder wünsch dir was!" />}
          {upcoming.map((ev) => (
            <EventCard key={ev.id} ev={ev} />
          ))}
        </div>
      ) : (
        <WeekView events={db.events.filter((e) => e.siteId === me.siteId)} offset={weekOffset} setOffset={setWeekOffset} />
      )}
    </Page>
  );
}

function EventCard({ ev }: { ev: SportEvent }) {
  const me = useMe()!;
  const now = useNow();
  const reg = registrationLabel(ev, me.id);
  const running = Date.parse(ev.start) <= now.getTime();
  const free = ev.capacity - ev.registered.length;
  return (
    <Link to={`/events/${ev.id}`} className="press block">
      <Card className="flex items-start gap-3">
        <EventDateTile start={ev.start} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            {running ? <Chip tone="success" icon={<Zap className="size-3" aria-hidden />}>Läuft gerade</Chip> : <Chip>{KIND_LABEL[ev.kind]}</Chip>}
            {reg.state === 'registered' && <Chip tone="accent">Angemeldet</Chip>}
            {reg.state === 'waitlist' && <Chip tone="warn">{reg.text}</Chip>}
          </div>
          <p className="mt-1.5 text-[17px] font-bold leading-snug">{ev.title}</p>
          <p className="mt-1 text-[13px] text-muted">
            {fmt.relativeDay(ev.start, now)} · {fmt.time(ev.start)} Uhr · {ev.location}
          </p>
          <div className="mt-2.5 flex items-center gap-2">
            <div className="flex-1">
              <ProgressBar value={Math.min(ev.registered.length, ev.capacity)} max={ev.capacity} label={`${ev.registered.length} von ${ev.capacity} Plätzen belegt`} height={6} tone={free <= 0 ? 'success' : 'accent'} />
            </div>
            <span className="tnum shrink-0 text-[12px] font-semibold text-muted">{free > 0 ? `${free} frei` : 'voll'}</span>
          </div>
        </div>
      </Card>
    </Link>
  );
}

function WeekView({ events, offset, setOffset }: { events: SportEvent[]; offset: number; setOffset: (n: number) => void }) {
  const now = useNow();
  const from = addDays(startOfWeek(now), offset * 7);
  const days = Array.from({ length: 7 }, (_, i) => addDays(from, i));
  return (
    <div className="mt-5">
      <div className="mb-3 flex items-center justify-between">
        <Button variant="secondary" size="sm" onClick={() => setOffset(offset - 1)} disabled={offset <= -1} aria-label="Vorherige Woche">
          ‹
        </Button>
        <p className="text-[15px] font-bold">
          {fmt.week(from)} · {fmt.date(from)} – {fmt.date(addDays(from, 6))}
        </p>
        <Button variant="secondary" size="sm" onClick={() => setOffset(offset + 1)} disabled={offset >= 3} aria-label="Nächste Woche">
          ›
        </Button>
      </div>
      <ol className="space-y-2">
        {days.map((d) => {
          const list = events.filter((e) => startOfDay(new Date(e.start)).getTime() === d.getTime()).sort((a, b) => Date.parse(a.start) - Date.parse(b.start));
          const today = startOfDay(now).getTime() === d.getTime();
          return (
            <li key={d.toISOString()} className={cx('flex gap-3 rounded-[18px] p-3', today ? 'bg-accent-soft' : 'bg-surface')}>
              <div className="w-11 shrink-0 text-center">
                <p className={cx('text-[12px] font-bold uppercase', today ? 'text-accent' : 'text-muted')}>{fmt.weekday(d)}</p>
                <p className={cx('tnum text-[20px] font-extrabold', today && 'text-accent')}>{d.getDate()}</p>
              </div>
              <div className="min-w-0 flex-1 space-y-1.5 self-center">
                {list.length === 0 && <p className="text-[14px] text-muted">–</p>}
                {list.map((e) => (
                  <Link key={e.id} to={`/events/${e.id}`} className="press flex min-h-11 items-center gap-2 rounded-[12px] bg-surface-2 px-3 py-2">
                    <span className="tnum text-[13px] font-bold text-accent">{fmt.time(e.start)}</span>
                    <span className="truncate text-[14px] font-semibold">{e.title}</span>
                  </Link>
                ))}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function EventDetail() {
  const { id } = useParams();
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const navigate = useNavigate();
  const toast = useToast();
  const ev = db.events.find((e) => e.id === id);
  if (!ev) return <Page><EmptyState icon={<CalendarDays />} title="Event nicht gefunden" /></Page>;
  const reg = registrationLabel(ev, me.id);
  const running = Date.parse(ev.start) <= now.getTime() && Date.parse(ev.end) > now.getTime();
  const past = Date.parse(ev.end) <= now.getTime();
  const reminder = ev.reminders.includes(me.id);
  const free = ev.capacity - ev.registered.length;
  const ownSite = ev.siteId === me.siteId;

  return (
    <Page>
      <div className="flex items-center justify-between pt-3">
        <IconButton label="Zurück" onClick={() => navigate(-1)}>
          <ArrowLeft className="size-5" />
        </IconButton>
        {reg.state !== 'none' && !past && (
          <IconButton
            label={reminder ? 'Erinnerung ausschalten' : 'Erinnerung einschalten'}
            onClick={async () => {
              const on = await api.toggleReminder(me.id, ev.id);
              toast(on ? 'Erinnerung ist an. Du bekommst vorher eine Benachrichtigung.' : 'Erinnerung ist aus.', 'info');
            }}
          >
            {reminder ? <Bell className="size-5 text-accent" /> : <BellOff className="size-5" />}
          </IconButton>
        )}
      </div>
      <div className="mt-4">
        <div className="flex flex-wrap gap-1.5">
          <Chip>{KIND_LABEL[ev.kind]}</Chip>
          <Chip tone="accent">+{ev.points} Punkte</Chip>
          {running && <Chip tone="success">Läuft gerade</Chip>}
          {past && <Chip>Vorbei</Chip>}
        </div>
        <h1 className="mt-3 text-[30px] font-extrabold leading-tight tracking-tight">{ev.title}</h1>
        {ev.description && <p className="mt-2 text-[16px] leading-relaxed text-ink-2">{ev.description}</p>}
      </div>
      <Card className="mt-5 divide-y divide-line p-0">
        <InfoRow icon={<CalendarDays className="size-5" />} label="Datum" value={fmt.relativeDay(ev.start, now)} />
        <InfoRow icon={<Clock className="size-5" />} label="Uhrzeit" value={`${fmt.time(ev.start)} – ${fmt.time(ev.end)} Uhr`} />
        <InfoRow icon={<MapPin className="size-5" />} label="Ort" value={ev.location} />
        <InfoRow icon={<Users className="size-5" />} label="Plätze" value={free > 0 ? `${free} von ${ev.capacity} frei` : `Ausgebucht · ${ev.waitlist.length} auf der Warteliste`} />
      </Card>
      {reg.state !== 'none' && (
        <p className="mt-4 text-center text-[15px] font-semibold text-accent" role="status">
          {reg.text}
        </p>
      )}
      {!past && ownSite && (
        <div className="mt-4 space-y-3">
          {running && (
            <Button size="lg" block icon={<QrCode className="size-5" />} onClick={() => navigate('/checkin')}>
              Jetzt einchecken
            </Button>
          )}
          {!running && (
            <Button
              size="lg"
              block
              variant={reg.state === 'none' ? 'primary' : 'secondary'}
              onClick={async () => {
                const r = await api.toggleRegistration(me.id, ev.id);
                toast(r.message, r.status === 'waitlist' ? 'info' : 'success');
              }}
            >
              {reg.action}
            </Button>
          )}
          <p className="text-center text-[13px] text-muted">Beim Event zeigt die Betreuung einen QR-Code zum Einchecken.</p>
        </div>
      )}
    </Page>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex min-h-14 items-center gap-3 px-4 py-3">
      <span className="text-muted" aria-hidden>
        {icon}
      </span>
      <span className="w-20 shrink-0 text-[14px] text-muted">{label}</span>
      <span className="min-w-0 flex-1 text-[15px] font-semibold">{value}</span>
    </div>
  );
}
