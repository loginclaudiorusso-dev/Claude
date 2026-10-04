import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Bell, CalendarDays, ChevronRight, Flame, MapPin, Megaphone, QrCode, ScanLine, Users, Zap } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { activitiesInWeek } from '../../domain/checkin';
import { activeSeason, personPoints, seasonRange, siteStandings, weekStreak } from '../../domain/league';
import { challengeProgress, currentWindow } from '../../domain/challenges';
import { addDays, fmt, startOfWeek } from '../../domain/time';
import { Avatar, Button, Card, Chip, IconButton, Page, ProgressBar, Ring, SectionHeader, TeamBadge, cx, useToast } from '../../components/ui';
import { DynIcon } from '../../components/DynIcon';
import { NotificationsSheet } from './NotificationsSheet';
import { EventDateTile, registrationLabel } from './Events';
import { TEAM_CLASSES } from '../../theme/teams';

export function Home() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const navigate = useNavigate();
  const toast = useToast();
  const [notifOpen, setNotifOpen] = useState(false);
  const site = db.sites.find((s) => s.id === me.siteId)!;

  const data = useMemo(() => {
    const weekFrom = startOfWeek(now);
    const weekTo = addDays(weekFrom, 7);
    const season = activeSeason(db);
    const [sFrom, sTo] = seasonRange(season, now);
    const nextEvent = db.events
      .filter((e) => e.siteId === me.siteId && Date.parse(e.end) > now.getTime())
      .sort((a, b) => Date.parse(a.start) - Date.parse(b.start))[0];
    const announcement = db.announcements.filter((a) => a.siteId === me.siteId).sort((a, b) => Date.parse(b.at) - Date.parse(a.at))[0];
    const weekly = db.challenges
      .filter((c) => c.active)
      .map((c) => currentWindow(c, now))
      .filter((c) => Date.parse(c.start) <= now.getTime() && Date.parse(c.end) > now.getTime())
      .map((c) => challengeProgress(db, c, me.id, now));
    return {
      weekPoints: personPoints(db, me.id, weekFrom, weekTo),
      weekCount: activitiesInWeek(db.checkins, me.id, now),
      streak: weekStreak(db.checkins, me.id, now),
      standings: siteStandings(db, sFrom, sTo),
      nextEvent,
      announcement: announcement && now.getTime() - Date.parse(announcement.at) < 5 * 86_400_000 ? announcement : undefined,
      unread: db.notifications.filter((n) => n.personId === me.id && !n.read).length,
      weekly,
    };
  }, [db, me.id, me.siteId, now]);

  const goal = db.settings.weeklyGoal;
  const maxPerActive = Math.max(1, ...data.standings.map((s) => s.perActive));

  return (
    <Page>
      {/* Kopfzeile */}
      <header className="flex items-center gap-3 pb-2 pt-3">
        <Avatar name={me.nickname} site={site} size={48} />
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-muted">{greeting(now)}</p>
          <h1 className="truncate text-[24px] font-extrabold leading-tight tracking-tight">Hallo, {me.nickname}!</h1>
        </div>
        <IconButton label={`Benachrichtigungen${data.unread ? `, ${data.unread} neu` : ''}`} badge={data.unread} onClick={() => setNotifOpen(true)}>
          <Bell className="size-[22px]" aria-hidden />
        </IconButton>
      </header>
      <div className="mb-4">
        <span className={cx('inline-flex items-center gap-2 rounded-pill py-1 pl-1 pr-3 text-[13px]', TEAM_CLASSES[site.team].soft)}>
          <TeamBadge site={site} size="sm" withName={false} />
          <span className="font-semibold text-ink">{site.teamName}</span>
        </span>
      </div>

      {/* Diese Woche */}
      <section aria-labelledby="week-title" className="anim-rise relative overflow-hidden rounded-card p-5 text-white shadow-card" style={{ background: 'linear-gradient(140deg, var(--hero-from), var(--hero-to))' }}>
        <div className="pointer-events-none absolute -right-16 -top-16 size-56 rounded-full bg-white/10 blur-2xl" aria-hidden />
        <div className="relative flex items-center justify-between">
          <h2 id="week-title" className="text-[13px] font-bold uppercase tracking-wider text-white/80">
            Diese Woche · {fmt.week(now)}
          </h2>
          {data.streak > 0 && (
            <span className="inline-flex items-center gap-1 rounded-pill bg-white/15 px-2.5 py-1 text-[12px] font-bold">
              <Flame className="size-3.5" aria-hidden /> {data.streak} {data.streak === 1 ? 'Woche' : 'Wochen'} Serie
            </span>
          )}
        </div>
        <div className="relative mt-4 flex items-center gap-5">
          <div className="text-white" style={{ ['--ring-from' as string]: 'var(--hero-ring-from)', ['--ring-to' as string]: 'var(--hero-ring-to)' }}>
            <Ring value={data.weekCount} max={goal} size={128} stroke={14} trackClass="text-white/15" label={`${data.weekCount} von ${goal} Aktivitäten im Wochenziel`}>
              <span className="tnum text-[34px] font-extrabold leading-none">{Math.min(data.weekCount, 99)}</span>
              <span className="mt-0.5 text-[12px] font-semibold text-white/75">von {goal}</span>
            </Ring>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-semibold text-white/75">Deine Punkte</p>
            <p className="tnum text-[44px] font-extrabold leading-none tracking-tight">{data.weekPoints}</p>
            <p className="mt-2 text-[14px] font-medium leading-snug text-white/90">
              {data.weekCount >= goal ? 'Wochenziel geschafft – stark!' : `Noch ${goal - data.weekCount} ${goal - data.weekCount === 1 ? 'Aktivität' : 'Aktivitäten'} bis zum Wochenziel.`}
            </p>
          </div>
        </div>
      </section>

      {/* Einchecken */}
      <Button size="lg" block className="mt-4 min-h-16 text-[18px] shadow-float" icon={<ScanLine className="size-6" aria-hidden />} onClick={() => navigate('/checkin')}>
        Einchecken
      </Button>

      {data.announcement && (
        <Card className="mt-4 flex items-start gap-3">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-warn-soft text-warn">
            <Megaphone className="size-5" aria-hidden />
          </span>
          <div className="min-w-0">
            <p className="text-[12px] font-semibold uppercase tracking-wide text-muted">
              Ankündigung · {fmt.relativeDay(data.announcement.at, now)}
            </p>
            <p className="mt-0.5 text-[15px] font-medium">{data.announcement.text}</p>
          </div>
        </Card>
      )}

      {/* Nächstes Event */}
      {data.nextEvent && (
        <>
          <SectionHeader title="Nächstes Event" action={<Link to="/events" className="min-h-11 content-center text-[15px] font-semibold text-accent">Alle</Link>} />
          <NextEventCard
            eventId={data.nextEvent.id}
            onToggle={async () => {
              const r = await api.toggleRegistration(me.id, data.nextEvent!.id);
              toast(r.message, r.status === 'waitlist' ? 'info' : 'success');
            }}
          />
        </>
      )}

      {/* Challenges */}
      <SectionHeader title="Deine Challenges" action={<Link to="/challenges" className="min-h-11 content-center text-[15px] font-semibold text-accent">Alle</Link>} />
      <div className="no-scrollbar -mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1">
        {data.weekly.slice(0, 4).map((p) => (
          <Link key={p.challenge.id} to="/challenges" className="press w-[220px] shrink-0 snap-start rounded-card bg-surface p-4 shadow-card">
            <div className="flex items-center justify-between">
              <span className={cx('flex size-10 items-center justify-center rounded-[12px]', p.status === 'geschafft' ? 'bg-success-soft text-success' : 'bg-accent-soft text-accent')}>
                <DynIcon name={p.challenge.icon} className="size-5" />
              </span>
              {p.status === 'geschafft' && <Chip tone="success">Geschafft</Chip>}
            </div>
            <p className="mt-3 truncate text-[16px] font-bold">{p.challenge.title}</p>
            <p className="tnum mb-2 mt-0.5 text-[13px] text-muted">
              {p.current} / {p.target} {p.challenge.scope === 'team' ? 'im Team' : ''}
            </p>
            <ProgressBar value={p.current} max={p.target} label={`${p.challenge.title}: ${p.current} von ${p.target}`} tone={p.status === 'geschafft' ? 'success' : 'accent'} height={8} />
          </Link>
        ))}
      </div>

      {/* Standort-Liga */}
      <SectionHeader title="Standort-Liga" action={<Link to="/liga" className="min-h-11 content-center text-[15px] font-semibold text-accent">Details</Link>} />
      <Card>
        <p className="mb-3 text-[13px] text-muted">Punkte pro aktivem Teilnehmenden in dieser Saison</p>
        <ol className="space-y-3">
          {data.standings.map((s) => {
            const st = db.sites.find((x) => x.id === s.siteId)!;
            const mine = st.id === me.siteId;
            return (
              <li key={s.siteId} className="flex items-center gap-3">
                <span className="tnum w-5 text-center text-[15px] font-bold text-muted">{s.rank}.</span>
                <span className="w-[118px] shrink-0 text-[14px]">
                  <TeamBadge site={st} size="sm" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="h-2.5 overflow-hidden rounded-full bg-surface-2">
                    <div className={cx('bar-progress h-full rounded-full', TEAM_CLASSES[st.team].bg)} style={{ width: `${(s.perActive / maxPerActive) * 100}%` }} />
                  </div>
                </div>
                <span className={cx('tnum w-12 text-right text-[15px] font-bold', mine && 'text-accent')}>{Math.round(s.perActive)}</span>
              </li>
            );
          })}
        </ol>
      </Card>
      <NotificationsSheet open={notifOpen} onClose={() => setNotifOpen(false)} />
    </Page>
  );
}

function NextEventCard({ eventId, onToggle }: { eventId: string; onToggle: () => void }) {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const ev = db.events.find((e) => e.id === eventId)!;
  const running = Date.parse(ev.start) <= now.getTime();
  const free = ev.capacity - ev.registered.length;
  const reg = registrationLabel(ev, me.id);
  return (
    <Card className="flex flex-col gap-3">
      <Link to={`/events/${ev.id}`} className="flex items-start gap-3">
        <EventDateTile start={ev.start} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            {running && <Chip tone="success" icon={<Zap className="size-3" aria-hidden />}>Läuft gerade</Chip>}
            {!running && <Chip>{fmt.relativeDay(ev.start, now)}</Chip>}
            <Chip tone="accent">+{ev.points} Punkte</Chip>
          </div>
          <p className="mt-1.5 text-[17px] font-bold leading-snug">{ev.title}</p>
          <p className="mt-1 flex items-center gap-1.5 text-[13px] text-muted">
            <CalendarDays className="size-3.5 shrink-0" aria-hidden /> {fmt.time(ev.start)} – {fmt.time(ev.end)} Uhr
          </p>
          <p className="mt-0.5 flex min-w-0 items-center gap-1.5 text-[13px] text-muted">
            <MapPin className="size-3.5 shrink-0" aria-hidden /> <span className="truncate">{ev.location}</span>
          </p>
        </div>
        <ChevronRight className="mt-1 size-5 shrink-0 text-muted" aria-hidden />
      </Link>
      <div className="flex items-center gap-3">
        <p className="flex flex-1 items-center gap-1.5 text-[13px] text-muted">
          <Users className="size-4" aria-hidden />
          {free > 0 ? `${free} von ${ev.capacity} Plätzen frei` : `Ausgebucht · ${ev.waitlist.length} auf der Warteliste`}
        </p>
        {running ? (
          <Link to="/checkin" className="press inline-flex min-h-12 items-center gap-2 rounded-pill bg-accent px-5 text-[15px] font-semibold text-accent-ink">
            <QrCode className="size-4" aria-hidden /> Einchecken
          </Link>
        ) : (
          <Button variant={reg.state === 'none' ? 'primary' : 'secondary'} onClick={onToggle}>
            {reg.action}
          </Button>
        )}
      </div>
    </Card>
  );
}

function greeting(now: Date) {
  const h = now.getHours();
  if (h < 11) return 'Guten Morgen';
  if (h < 17) return 'Schön, dass du da bist';
  return 'Guten Abend';
}
