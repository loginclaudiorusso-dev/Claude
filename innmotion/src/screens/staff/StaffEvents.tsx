import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarPlus, Send } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { addDays, fmt } from '../../domain/time';
import type { EventKind, SportEvent } from '../../domain/types';
import { Avatar, Button, Card, Chip, Field, inputCls, LargeTitle, Page, ProgressBar, SectionHeader, Segmented, Sheet, useToast } from '../../components/ui';
import { EventDateTile, KIND_LABEL } from '../participant/Events';
import { BackHeader } from '../participant/ProfilePages';

export function StaffEvents() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const navigate = useNavigate();
  const [tab, setTab] = useState<'next' | 'past'>('next');
  const [detail, setDetail] = useState<SportEvent | null>(null);
  const list = db.events
    .filter((e) => e.siteId === me.siteId && (tab === 'next' ? Date.parse(e.end) > now.getTime() : Date.parse(e.end) <= now.getTime()))
    .sort((a, b) => (tab === 'next' ? 1 : -1) * (Date.parse(a.start) - Date.parse(b.start)));

  return (
    <Page>
      <LargeTitle
        title="Events"
        trailing={
          <Button icon={<CalendarPlus className="size-5" />} onClick={() => navigate('/betreuung/events/neu')}>
            Neu
          </Button>
        }
      />
      <Segmented label="Zeitraum" value={tab} onChange={setTab} options={[{ value: 'next', label: 'Kommend' }, { value: 'past', label: 'Vergangen' }]} />
      <ul className="mt-4 space-y-3">
        {list.map((e) => {
          const attended = db.checkins.filter((c) => c.target.type === 'event' && c.target.eventId === e.id).length;
          return (
            <li key={e.id}>
              <button type="button" onClick={() => setDetail(e)} className="press block w-full text-left">
                <Card className="flex items-start gap-3">
                  <EventDateTile start={e.start} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap gap-1.5">
                      <Chip>{KIND_LABEL[e.kind]}</Chip>
                      {e.waitlist.length > 0 && <Chip tone="warn">{e.waitlist.length} Warteliste</Chip>}
                    </div>
                    <p className="mt-1.5 font-bold">{e.title}</p>
                    <p className="text-[13px] text-muted">
                      {fmt.time(e.start)} Uhr · {e.location}
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1">
                        <ProgressBar value={Math.min(e.registered.length, e.capacity)} max={e.capacity} label={`Auslastung ${e.title}`} height={6} />
                      </div>
                      <span className="tnum text-[12px] font-semibold text-muted">
                        {tab === 'next' ? `${e.registered.length}/${e.capacity}` : `${attended} da`}
                      </span>
                    </div>
                  </div>
                </Card>
              </button>
            </li>
          );
        })}
      </ul>
      {detail && <EventPeopleSheet ev={detail} onClose={() => setDetail(null)} />}
    </Page>
  );
}

function EventPeopleSheet({ ev, onClose }: { ev: SportEvent; onClose: () => void }) {
  const db = useDb();
  const site = db.sites.find((s) => s.id === ev.siteId);
  const name = (id: string) => db.persons.find((p) => p.id === id)?.nickname ?? 'Gelöschtes Konto';
  const live = db.events.find((e) => e.id === ev.id) ?? ev;
  return (
    <Sheet open onClose={onClose} title={live.title}>
      <p className="text-[14px] text-muted">
        {fmt.dateTime(live.start)} · {live.registered.length} von {live.capacity} Plätzen · +{live.points} Punkte
      </p>
      <SectionHeader title={`Angemeldet (${live.registered.length})`} />
      <ul className="grid grid-cols-2 gap-2">
        {live.registered.map((id) => (
          <li key={id} className="flex min-h-12 items-center gap-2 rounded-[14px] bg-surface-2 px-3">
            <Avatar name={name(id)} site={site} size={28} />
            <span className="truncate text-[14px] font-semibold">{name(id)}</span>
          </li>
        ))}
      </ul>
      {live.waitlist.length > 0 && (
        <>
          <SectionHeader title={`Warteliste (${live.waitlist.length})`} />
          <ol className="space-y-2">
            {live.waitlist.map((id, i) => (
              <li key={id} className="flex min-h-12 items-center gap-3 rounded-[14px] bg-surface-2 px-3 text-[14px] font-semibold">
                <span className="tnum text-muted">{i + 1}.</span> {name(id)}
              </li>
            ))}
          </ol>
        </>
      )}
    </Sheet>
  );
}

const pad = (n: number) => String(n).padStart(2, '0');
const localInput = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;

export function NewEvent() {
  const me = useMe()!;
  const db = useDb();
  const navigate = useNavigate();
  const toast = useToast();
  const site = db.sites.find((s) => s.id === me.siteId)!;
  const defaultStart = addDays(new Date(new Date().setHours(18, 0, 0, 0)), 2);
  const [f, setF] = useState({
    title: '',
    kind: 'themenabend' as EventKind,
    sport: '',
    location: `Sporthalle ${site.name}`,
    start: localInput(defaultStart),
    duration: 90,
    capacity: 16,
    points: 15,
    description: '',
  });
  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF({ ...f, [k]: v });
  const valid = f.title.trim().length >= 3 && f.sport.trim().length >= 2 && f.capacity > 0;

  return (
    <Page>
      <BackHeader />
      <LargeTitle title="Event anlegen" subtitle={`Alle in ${site.name} werden benachrichtigt.`} />
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (!valid) return;
          const start = new Date(f.start);
          await api.createEvent({
            siteId: me.siteId,
            title: f.title.trim(),
            kind: f.kind,
            sport: f.sport.trim(),
            location: f.location.trim(),
            start: start.toISOString(),
            end: new Date(start.getTime() + f.duration * 60000).toISOString(),
            capacity: f.capacity,
            points: f.points,
            description: f.description.trim(),
          });
          toast('Event angelegt und angekündigt.');
          navigate('/betreuung/events');
        }}
      >
        <Field label="Titel">{(id) => <input id={id} className={inputCls} value={f.title} onChange={(e) => set('title', e.target.value)} placeholder="z. B. Fußball-Nacht" maxLength={60} />}</Field>
        <Field label="Art">
          {(id) => (
            <select id={id} className={inputCls} value={f.kind} onChange={(e) => set('kind', e.target.value as EventKind)}>
              {(Object.keys(KIND_LABEL) as EventKind[]).map((k) => (
                <option key={k} value={k}>
                  {KIND_LABEL[k]}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field label="Sportart / Angebot" hint="Zählt für das Abzeichen „Allrounder“.">
          {(id) => <input id={id} className={inputCls} value={f.sport} onChange={(e) => set('sport', e.target.value)} placeholder="z. B. Fußball" maxLength={30} list="sports" />}
        </Field>
        <datalist id="sports">
          {[...new Set(db.events.map((e) => e.sport))].map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
        <Field label="Ort">{(id) => <input id={id} className={inputCls} value={f.location} onChange={(e) => set('location', e.target.value)} maxLength={60} />}</Field>
        <Field label="Beginn">{(id) => <input id={id} type="datetime-local" className={inputCls} value={f.start} onChange={(e) => set('start', e.target.value)} />}</Field>
        <div className="grid grid-cols-3 gap-3">
          <Field label="Dauer (Min.)">{(id) => <input id={id} type="number" inputMode="numeric" min={15} step={15} className={inputCls} value={f.duration} onChange={(e) => set('duration', Number(e.target.value) || 60)} />}</Field>
          <Field label="Plätze">{(id) => <input id={id} type="number" inputMode="numeric" min={1} className={inputCls} value={f.capacity} onChange={(e) => set('capacity', Number(e.target.value) || 1)} />}</Field>
          <Field label="Punkte">{(id) => <input id={id} type="number" inputMode="numeric" min={0} max={30} className={inputCls} value={f.points} onChange={(e) => set('points', Number(e.target.value) || 0)} />}</Field>
        </div>
        <Field label="Beschreibung (optional)">{(id) => <textarea id={id} className={inputCls + ' min-h-24 py-3'} value={f.description} onChange={(e) => set('description', e.target.value)} maxLength={300} />}</Field>
        <Button type="submit" size="lg" block disabled={!valid}>
          Event anlegen
        </Button>
      </form>
    </Page>
  );
}

export function Announcement() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const toast = useToast();
  const [text, setText] = useState('');
  const site = db.sites.find((s) => s.id === me.siteId)!;
  const history = db.announcements.filter((a) => a.siteId === me.siteId);
  return (
    <Page>
      <BackHeader />
      <LargeTitle title="Ankündigung" subtitle={`Kurze Nachricht an alle Teilnehmenden in ${site.name}.`} />
      <Card>
        <label htmlFor="ann" className="sr-only">
          Nachricht
        </label>
        <textarea id="ann" className={inputCls + ' min-h-32 py-3'} value={text} onChange={(e) => setText(e.target.value)} maxLength={200} placeholder="z. B. Die Halle ist heute ab 18 Uhr wegen Reinigung geschlossen." />
        <div className="mt-2 flex items-center justify-between">
          <span className="tnum text-[12px] text-muted">{text.length}/200</span>
          <Button
            icon={<Send className="size-4" />}
            disabled={text.trim().length < 5}
            onClick={async () => {
              const n = await api.sendAnnouncement(me.siteId, me.nickname, text.trim());
              setText('');
              toast(`Gesendet an ${n} Personen mit eingeschalteten Benachrichtigungen.`);
            }}
          >
            Senden
          </Button>
        </div>
      </Card>
      <SectionHeader title="Zuletzt gesendet" />
      <ul className="space-y-2">
        {history.map((a) => (
          <li key={a.id}>
            <Card>
              <p className="text-[12px] text-muted">
                {fmt.relativeDay(a.at, now)}, {fmt.time(a.at)} · {a.author}
              </p>
              <p className="mt-1 text-[15px]">{a.text}</p>
            </Card>
          </li>
        ))}
      </ul>
    </Page>
  );
}
