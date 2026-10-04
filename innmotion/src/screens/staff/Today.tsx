import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarPlus, Lightbulb, Megaphone, Pencil, QrCode, Trash2, UserPlus, Users } from 'lucide-react';
import { api } from '../../services/mock/mockApi';
import { useDb, useMe, useNow } from '../../services/hooks';
import { addDays, fmt, startOfDay } from '../../domain/time';
import type { Checkin } from '../../domain/types';
import { Avatar, Button, Card, Chip, EmptyState, Field, inputCls, LargeTitle, Page, SectionHeader, Sheet, Stat, useToast } from '../../components/ui';

export function StaffToday() {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const navigate = useNavigate();
  const site = db.sites.find((s) => s.id === me.siteId)!;
  const [edit, setEdit] = useState<Checkin | null>(null);
  const [addOpen, setAddOpen] = useState(false);

  const today = useMemo(() => {
    const from = startOfDay(now);
    const to = addDays(from, 1);
    return db.checkins
      .filter((c) => c.siteId === me.siteId && Date.parse(c.at) >= from.getTime() && Date.parse(c.at) < to.getTime())
      .sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
  }, [db.checkins, me.siteId, now]);
  const people = new Set(today.map((c) => c.personId)).size;
  const eventsToday = db.events.filter((e) => e.siteId === me.siteId && startOfDay(new Date(e.start)).getTime() === startOfDay(now).getTime());
  const targetLabel = (c: Checkin) =>
    c.target.type === 'place' ? db.places.find((p) => p.id === (c.target as { placeId: string }).placeId)?.name ?? 'Ort' : db.events.find((e) => e.id === (c.target as { eventId: string }).eventId)?.title ?? 'Event';

  return (
    <Page>
      <LargeTitle eyebrow={`Betreuung · ${site.name}`} title="Heute" subtitle={fmt.relativeDay(now, now) + ', ' + now.toLocaleDateString('de-DE', { day: 'numeric', month: 'long' })} />
      <div className="grid grid-cols-3 gap-2.5">
        <Stat label="Check-ins" value={today.length} />
        <Stat label="Personen" value={people} />
        <Stat label="Events" value={eventsToday.length} />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2.5">
        <QuickAction icon={<QrCode className="size-6" />} label="Code zeigen" onClick={() => navigate('/betreuung/code')} primary />
        <QuickAction icon={<CalendarPlus className="size-6" />} label="Event anlegen" onClick={() => navigate('/betreuung/events/neu')} />
        <QuickAction icon={<Megaphone className="size-6" />} label="Ankündigung" onClick={() => navigate('/betreuung/ankuendigung')} />
        <QuickAction icon={<Lightbulb className="size-6" />} label="Ideen" onClick={() => navigate('/betreuung/ideen')} />
      </div>

      <SectionHeader
        title="Teilnahmen heute"
        action={
          <Button size="sm" variant="soft" icon={<UserPlus className="size-4" />} onClick={() => setAddOpen(true)}>
            Nachtragen
          </Button>
        }
      />
      {today.length === 0 ? (
        <Card>
          <EmptyState icon={<Users />} title="Noch keine Check-ins heute" text="Zeig den QR-Code am Eingang – dann geht es los." />
        </Card>
      ) : (
        <Card className="p-0">
          <ul>
            {today.map((c) => {
              const p = db.persons.find((x) => x.id === c.personId);
              return (
                <li key={c.id} className="flex min-h-16 items-center gap-3 border-t border-line px-4 py-2.5 first:border-t-0">
                  <Avatar name={p?.nickname ?? '?'} site={site} size={38} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{p?.nickname ?? 'Gelöschtes Konto'}</p>
                    <p className="truncate text-[13px] text-muted">
                      {fmt.time(c.at)} · {targetLabel(c)}
                      {c.source === 'staff' && ' · nachgetragen'}
                    </p>
                  </div>
                  <Chip tone="accent">+{c.points}</Chip>
                  <button type="button" onClick={() => setEdit(c)} aria-label={`Teilnahme von ${p?.nickname} bearbeiten`} className="press flex size-11 items-center justify-center rounded-full text-muted hover:bg-surface-2">
                    <Pencil className="size-4" aria-hidden />
                  </button>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
      {edit && <EditCheckinSheet checkin={edit} onClose={() => setEdit(null)} />}
      <AddCheckinSheet open={addOpen} onClose={() => setAddOpen(false)} />
    </Page>
  );
}

function QuickAction({ icon, label, onClick, primary }: { icon: React.ReactNode; label: string; onClick: () => void; primary?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`press flex min-h-[88px] flex-col items-start justify-between rounded-[20px] p-4 text-left text-[15px] font-bold shadow-card ${primary ? 'bg-accent text-accent-ink' : 'bg-surface text-ink'}`}
    >
      <span aria-hidden>{icon}</span>
      {label}
    </button>
  );
}

function EditCheckinSheet({ checkin, onClose }: { checkin: Checkin; onClose: () => void }) {
  const db = useDb();
  const toast = useToast();
  const [points, setPoints] = useState(checkin.points);
  const person = db.persons.find((p) => p.id === checkin.personId);
  return (
    <Sheet
      open
      onClose={onClose}
      title="Teilnahme korrigieren"
      footer={
        <div className="flex gap-3">
          <Button
            variant="danger"
            icon={<Trash2 className="size-4" />}
            onClick={async () => {
              await api.removeCheckin(checkin.id);
              toast('Teilnahme entfernt.');
              onClose();
            }}
          >
            Entfernen
          </Button>
          <Button
            block
            onClick={async () => {
              await api.adjustCheckinPoints(checkin.id, points);
              toast('Punkte gespeichert.');
              onClose();
            }}
          >
            Speichern
          </Button>
        </div>
      }
    >
      <p className="text-[15px] text-ink-2">
        <strong className="text-ink">{person?.nickname}</strong> · {fmt.time(checkin.at)} Uhr
      </p>
      <ul className="my-3 space-y-1 rounded-[14px] bg-surface-2 p-3 text-[14px]">
        {checkin.breakdown.map((b, i) => (
          <li key={i} className="flex justify-between">
            <span className="text-ink-2">{b.label}</span>
            <span className="tnum font-semibold">{b.points > 0 ? `+${b.points}` : b.points}</span>
          </li>
        ))}
      </ul>
      <Field label="Punkte" hint="Z. B. wenn jemand doppelt eingecheckt hat oder ein Bonus fehlt.">
        {(id) => <input id={id} type="number" inputMode="numeric" min={0} max={60} className={inputCls} value={points} onChange={(e) => setPoints(Math.max(0, Math.min(60, Number(e.target.value) || 0)))} />}
      </Field>
    </Sheet>
  );
}

function AddCheckinSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const db = useDb();
  const me = useMe()!;
  const now = useNow();
  const toast = useToast();
  const people = db.persons.filter((p) => p.role === 'participant' && p.siteId === me.siteId).sort((a, b) => a.nickname.localeCompare(b.nickname));
  const targets = [
    ...db.places.filter((p) => p.siteId === me.siteId && p.active).map((p) => ({ id: p.id, label: p.name })),
    ...db.events.filter((e) => e.siteId === me.siteId && Date.parse(e.start) - 30 * 60000 <= now.getTime() && Date.parse(e.end) >= now.getTime()).map((e) => ({ id: e.id, label: e.title })),
  ];
  const [personId, setPersonId] = useState(people[0]?.id ?? '');
  const [targetId, setTargetId] = useState(targets[0]?.id ?? '');
  return (
    <Sheet
      open={open}
      onClose={onClose}
      title="Teilnahme nachtragen"
      footer={
        <Button
          block
          disabled={!personId || !targetId}
          onClick={async () => {
            const r = await api.addManualCheckin(personId, targetId);
            if (r.ok) {
              toast(`Nachgetragen: +${r.points} Punkte.`);
              onClose();
            } else toast(r.reason, 'error');
          }}
        >
          Nachtragen
        </Button>
      }
    >
      <p className="mb-4 text-[14px] text-ink-2">Für alle ohne Handy – die gleichen Regeln wie beim Check-in gelten (3-Stunden-Sperre, Tagesobergrenze).</p>
      <Field label="Person">
        {(id) => (
          <select id={id} className={inputCls} value={personId} onChange={(e) => setPersonId(e.target.value)}>
            {people.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nickname}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Field label="Ort / Event">
        {(id) => (
          <select id={id} className={inputCls} value={targetId} onChange={(e) => setTargetId(e.target.value)}>
            {targets.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        )}
      </Field>
    </Sheet>
  );
}
